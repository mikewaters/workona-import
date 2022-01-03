"""
This is a bunch of code for interfacing with Workona export files.
1. PyYAML componentry for fixing the quoting defects, for Workona workspaces that 
contain yaml control characters in their names (easy ones, like ':').
2. Function for exporting Workona export data (sourced via JSON or YAML) to non-Workona systems.
"""
import yaml
from copy import copy
from functools import partial
from yaml.nodes import MappingNode, ScalarNode

class WorkonaMappingNodeComposer(yaml.composer.Composer):
    """
    Subclass of `yaml.composer.Composer` that conditionally uses
    custom Scanner/Reader classes to fix missing string quoting in some
    cases for Workona personal data exports.
    """
    # The Workona export emits a bunch if information.
    # but these are the only mapping keys I've seen
    # that need to be fixed.
    UNQUOTED_NODE_KEYS = ('title', 'description')

    def compose_node(self, parent, index):
        """Modify the buffer, if necessary, before moving on to `compose_node()`;
        this method call causes a tokenization pass that reads from the buffer, 
        and will behave wrongly due to unquoted strings, so we need to fix it.
        
        It would be more correct astractly to hook into `Composer.compose_mapping_node`,
        however the logic does not allow it. 
        """        
        # From the call signature, we can infer that this call will build the value
        # part of a key/vaue pair.
        if isinstance(parent, MappingNode) and isinstance(index, ScalarNode):
            if index.value in self.UNQUOTED_NODE_KEYS:
                # the method we're calling will handle any lower-level checks
                self.patch_buffer_for_unquoted_scalar()

        return super().compose_node(parent, index)

class WorkonaQuotePatchReaderMixin(object):
    """
    Add functionality to a `yaml.reader.Reader` to patch the buffer, injecting quotes
    into strategic locations to fix higher-level tokenization.
    """
    def patch_buffer_for_unquoted_scalar(self):
        """
        From the current buffer seek position, assuming the next event will be `ScalarEvent`,`
        read through to the end of the current line and wrap the results in quotes.  If there 
        are any existing quotes, escape them.
        It would be much nicer to recreate the quoting code from `yaml.emitter.Emitter`,
        but holy smoke that is dense!2
        """
        # seek to the first non-space character, as this is where
        # our token should start
        while self.peek() == ' ':
            self.forward()

        idx = 0
        scalar = ''
        # Loop through the buffer and find single-line strings that
        # need to be quoted.
        while 1:
            # Lean on `Reader.peek` method to read from the buffer. 
            # For the edge cases where a scalar we might need to fix
            # is only partially loaded into the buffer, `peek` will
            # transparently update the buffer from the yaml document stream.
            # As long as we don't advance `self.pointer`, the Reader will
            # append to the buffer and nothing terrible will happen. 
            ch = self.peek(idx)
            # stolen from yaml.scanner.Scanner
            if ch in '\0\r\n\x85\u2028\u2029': 
                break 
            scalar = scalar+ch
            idx+=1

        # bail if this is a blank line
        if not len(scalar): 
            return

        # bail if we find a number-ish value
        try:
            int(scalar)
        except:
            pass
        else:
            return

        # We'll need this later if we have to mangle the orig string
        original_sz = len(scalar)

        if '"' in scalar:
            # escape doublequotes
            scalar = scalar.replace('"', r'\"')
        
        # TODO:
        # There only certain cases that *require* quoting, like
        # valid yaml tokens appearing in text (':' and others).
        # A smarter method would take this into account, instead of
        # brute-forcing.
        # This is not a smarter method.

        # shwap
        end = self.pointer+original_sz
        self.buffer = (
            f"{self.buffer[:self.pointer]}"
            f"\"{scalar}\""
            f"{self.buffer[end:]}"
        )    

class ConfigurableBufferedReader(yaml.reader.Reader):
    """
    Subclass of `yaml.reader.Reader` that allows the
    buffer size to be configurable at initialization time.

    This allows the buffer size to be confugured without ripping into
    other parts of the codebase.
    """
    def __init__(self, stream, buffer_sz=4096):
        self.buffer_sz = buffer_sz
        super().__init__(stream)

    def update_raw(self, size=None):
        if size is None:
            size = self.buffer_sz
        return super().update_raw(size=size)

class VerboseParser(yaml.parser.Parser):
    """
    Parser subclass that logs the history of events, which
    is useful for debugging issues with bad YAML documents.

    It turns the instance variable `Parser.current_event` 
    into a property, so it can hook into the setter without
    changing any existing code.
    """
    def __init__(self):
        super().__init__()
        self._current_event = None

    @property
    def current_event(self):
        return self._current_event

    @current_event.setter
    def current_event(self, value):
        self._current_event = value 
        if not hasattr(self, '_event_history'):
            self._event_history = list()
        if value: self._event_history.append(value)


class VerboseScanner(yaml.scanner.Scanner):
    """
    Scanner subclass that logs the history
    of tokens, which is useful for debugging.

    When a token is removed from the `Scanner.tokens` instance
    variable stack, that token is added to a private instance 
    variable dictionary keyed to the `Scanner.tokens_taken`
    instance variable, which is a pattern used elsewhere.
    """
    def get_token(self):
        # Change default behavior to keep a history
        # of tokens, in order to better understand how
        # this beautiful module works.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            t = self.tokens.pop(0)

            # populate a token cache so we can inspect it later
            if not hasattr(self, '_token_history'):
                self._token_history = dict()
            self._token_history[self.tokens_taken] = t

            return t

class WorkonaExportLoader(
    ConfigurableBufferedReader, 
    VerboseScanner, 
    VerboseParser, 
    WorkonaMappingNodeComposer,
    yaml.constructor.FullConstructor,
    yaml.resolver.Resolver, 
    WorkonaQuotePatchReaderMixin
    ):
    def __init__(self, stream, buffer_sz):
        # The initialization order appears to be important:
        #  Reader, Scanner, Parser, Composer, Constructor, Resolver
        ConfigurableBufferedReader.__init__(self, stream, buffer_sz=buffer_sz)
        VerboseScanner.__init__(self)
        VerboseParser.__init__(self)
        WorkonaMappingNodeComposer.__init__(self)
        yaml.constructor.FullConstructor.__init__(self)
        yaml.resolver.Resolver.__init__(self)


def yaml_load(data):
    """Wrapper of `yaml.load`.
    By the way, it was very nice of the PyYAML devs to write *one* load
    method that accepts a string or stream, not like the folks over at JSON.
    """
    return yaml.load(data, Loader=partial(WorkonaExportLoader, buffer_sz=4096))

def make_bookmarks(data, workspaces=None, wrapped=True):
    """Generate quick-and-dirty chrome-compatible bookmark import text.

    :param data: dictionary representation of an entire Workona export file
    :type data: dict
    :param workspaces: 'titles' of workspaces that you want to see in output exclusively
    :type workspaces: list
    :param wrapped: whether to wrap all bookmarks in a top-level "Workona Export" folder
    :type wrapped: bool
    :return: bookmarks document html data
    :rtype: str

    A note on the use of `enumerate`:
    In the case of a yaml export source, the `data` dictionary will have an ordered
    structure; in the case of JSON, however, it will be un-ordered.  Presumably, 
    the Workona designers believe JSON to guarantee array order, because that's 
    how Javascript behaves.  However, this is not guaranteed by the ECMA JSON spec, 
    and consequently there may be a JSON implementation that does not enforce array order.  
    At the end of the day though, only Workona knows which of their systems will be 
    de/serializing their JSON, and which of those enforce order or do not.

    I can only think that they are going to de[precate the yaml export, otherwise they will 
    need to maintain two export data structures.

    Example `dict` from yaml:
    ```
    {
      'Workspaces': {
        0: {
          'title': ...
        }
      }
    }
    ```
    From json:
    ```
    {
      'Workspaces': [
        {
          'title': ...
        }
      ]
    }
    ```
    """
    output = []
    wrapper = "Workona Export"
    filtered = {}

    if workspaces:
        filtered = {'Workspaces': {}}
        seq = 0
        for widx, wvalue in enumerate(data['Workspaces']):
            if widx == wvalue:
                # yaml source
                workspace = data['Workspaces'][wvalue]
            else:
                workspace = wvalue
            
            if workspace['title'] in workspaces:
                filtered['Workspaces'][seq] = copy(workspace)
                seq += 1

        data = filtered

    # This preamble is not per the spec (see readme [1]), it was taken from a Chrome export.
    output.append("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
    output.append('<!<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')

    output.append("<DL><p>")

    if wrapped: output.append(f"<DT><H3 FOLDED>{wrapper}</H3>\n<DL>")

    for widx, wvalue in enumerate(data['Workspaces']):
        if widx == wvalue:
            # we have yaml source
            workspace = data['Workspaces'][wvalue]
        else:
            workspace = wvalue

        title = workspace['title']

        output.append(f"\t<DT><H3 FOLDED>{title}</H3>")
        output.append("\t\t<DL><p>")

        if 'tabs' in workspace:
            for tidx, tvalue in enumerate(workspace['tabs']):
                if tidx == tvalue:
                    # again, yaml
                    tab = workspace['tabs'][tidx]
                else:
                    tab = tvalue

                url = tab['url']
                desc = tab.get('title', url)

                output.append(f'\t\t\t<DT><A HREF="{url}">{desc}</a>')

        output.append("\t\t</DL>")
        output.append("\t</DT>")

    if wrapped: output.append(f"</DL></DT>")

    output.append("</DL>")

    return "\n".join(output)
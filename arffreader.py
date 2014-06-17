import re
import csv

# CONSTANTS ===================================================================
__author__ = 'Renato de Pontes Pereira'
__author_email__ = 'renato.ppontes@gmail.com'
__version__ = '2.0.2'
__adapted_by__ = 'Arturo Jiménez López'
_SIMPLE_TYPES = ['NUMERIC', 'REAL', 'INTEGER', 'STRING']

_TK_DESCRIPTION = '%'
_TK_COMMENT     = '%'
_TK_RELATION    = '@RELATION'
_TK_ATTRIBUTE   = '@ATTRIBUTE'
_TK_DATA        = '@DATA'
_TK_VALUE       = ''

_RE_RELATION     = re.compile(r'^(\".*\"|\'.*\'|\S*)$', re.UNICODE)
_RE_ATTRIBUTE    = re.compile(r'^(\".*\"|\'.*\'|\S*)\s+(.+)$', re.UNICODE)
_RE_TYPE_NOMINAL = re.compile(r'^\{\s*((\".*\"|\'.*\'|\S*)\s*,\s*)*(\".*\"|\'.*\'|\S*)}$', re.UNICODE)
_RE_ESCAPE = re.compile(r'\\\'|\\\"|\\\%|[\\"\'%]')

_ESCAPE_DCT = {
    ' ': ' ',
    "'": "\\'",
    '"': '\\"',
    '%': '\\%',
    '\\': '\\',
    '\\\'': '\\\'',
    '\\"': '\\"',
    '\\%': '\\%',
}
# =============================================================================

# COMPATIBILITY WITH PYTHON 3.3 ===============================================

# =============================================================================
#Esta clase, así como sus métodos son la readaptación de un módulo para poder leer los ficheros arff
# EXCEPTIONS ==================================================================


class ArffException(Exception):
    message = None

    def __init__(self):
        self.line = -1

    def __str__(self):
        return self.message%self.line


class BadRelationFormat(ArffException):
    '''Error raised when the relation declaration is in an invalid format.'''
    message = 'Bad @RELATION format, at line %d.'


class BadAttributeFormat(ArffException):
    '''Error raised when some attribute declaration is in an invalid format.'''
    message = 'Bad @ATTIBUTE format, at line %d.'


class BadDataFormat(ArffException):
    '''Error raised when some data instance is in an invalid format.'''
    message = 'Bad @DATA instance format, at line %d.'


class BadAttributeType(ArffException):
    '''Error raised when some invalid type is provided into the attribute
    declaration.'''
    message = 'Bad @ATTRIBUTE type, at line %d.'


class BadNominalValue(ArffException):
    '''Error raised when a value in used in some data instance but is not
    declared into it respective attribute declaration.'''
    message = 'Data value not found in nominal declaration, at line %d.'


class BadNumericalValue(ArffException):
    '''Error raised when and invalid numerical value is used in some data
    instance.'''
    message = 'Invalid numerical value, at line %d.'


class BadLayout(ArffException):
    '''Error raised when the layout of the ARFF file has something wrong.'''
    message = 'Invalid layout of the ARFF file, at line %d.'


class BadObject(ArffException):
    '''Error raised when the object representing the ARFF file has something
    wrong.'''

    def __str__(self):
        return 'Invalid object.'


class BadObject(ArffException):
    '''Error raised when the object representing the ARFF file has something
    wrong.'''
    def __init__(self, msg=''):
        self.msg = msg

    def __str__(self):
        return '%s'%self.msg
# =============================================================================

# INTERNAL ====================================================================

#Esta clase, así como sus métodos son la readaptación de un módulo para poder leer los ficheros arff


def encode_string(s):
    def replace(match):
        return _ESCAPE_DCT[match.group(0)]
    return u"'" + _RE_ESCAPE.sub(replace, s) + u"'"


class Conversor(object):
    '''Conversor is a helper used for converting ARFF types to Python types.'''

    def __init__(self, type_, values=None):
        '''Contructor.'''

        self.values = values

        if type_ == 'NUMERIC' or type_ == 'REAL':
            self._conversor = self._float
        elif type_ == 'STRING':
            self._conversor = self._string
        elif type_ == 'INTEGER':
            self._conversor = self._integer
        elif type_ == 'NOMINAL':
            self._conversor = self._nominal
        else:
            raise BadAttributeType()

    def _float(self, value):
        '''Convert the value to float.'''
        try:
            return float(value)
        except ValueError as e:
            raise BadNumericalValue()

    def _integer(self, value):
        '''Convert the value to integer.'''
        try:
            return int(float(value))
        except ValueError as e:
            raise BadNumericalValue()

    def _string(self, value):
        '''Convert the value to string.'''
        return str(value)

    def _nominal(self, value):
        '''Verify the value of nominal attribute and convert it to string.'''
        if value not in self.values:
            raise BadNominalValue()

        return self._string(value)

    def __call__(self, value):
        '''Convert a ``value`` to a given type.

        This function also verify if the value is an empty string or a missing
        value, either cases, it returns None.
        '''
        value = value.strip(' ').strip('\"\'')

        if value == u'?' or value == u'':
            return None

        return self._conversor(value)
# =============================================================================

# ADVANCED INTERFACE ==========================================================

#Esta clase, así como sus métodos son la readaptación de un módulo para poder leer los ficheros arff


class ArffDecoder(object):
    '''An ARFF decoder.'''

    def __init__(self):
        '''Constructor.'''
        self._conversors = []
        self._current_line = 0

    def _decode_comment(self, s):
        '''(INTERNAL) Decodes a comment line.

        Comments are single line strings starting, obligatorily, with the ``%``
        character, and can have any symbol, including whitespaces or special
        characters.

        This method must receive a normalized string, i.e., a string without
        padding, including the "\r\n" characters.

        :param s: a normalized string.
        :return: a string with the decoded comment.
        '''
        res = re.sub('^\%( )?', '', s)
        return res

    def _decode_relation(self, s):
        '''(INTERNAL) Decodes a relation line.

        The relation declaration is a line with the format ``@RELATION
        <relation-name>``, where ``relation-name`` is a string. The string must
        be quoted if the name includes spaces, otherwise this method will raise
        a `BadRelationFormat` exception.

        This method must receive a normalized string, i.e., a string without
        padding, including the "\r\n" characters.

        :param s: a normalized string.
        :return: a string with the decoded relation name.
        '''
        _, v = s.split(' ', 1)
        v = v.strip()

        if not _RE_RELATION.match(v):
            raise BadRelationFormat()

        res = str(v.strip('"\''))
        return res

    def _decode_attribute(self, s):
        '''(INTERNAL) Decodes an attribute line.

        The attribute is the most complex declaration in an arff file. All
        attributes must follow the template::

             @attribute <attribute-name> <datatype>

        where ``attribute-name`` is a string, quoted if the name contains any
        whitespace, and ``datatype`` can be:

        - Numerical attributes as ``NUMERIC``, ``INTEGER`` or ``REAL``.
        - Strings as ``STRING``.
        - Dates (NOT IMPLEMENTED).
        - Nominal attributes with format:

            {<nominal-name1>, <nominal-name2>, <nominal-name3>, ...}

        The nominal names follow the rules for the attribute names, i.e., they
        must be quoted if the name contains whitespaces.

        This method must receive a normalized string, i.e., a string without
        padding, including the "\r\n" characters.

        :param s: a normalized string.
        :return: a tuple (ATTRIBUTE_NAME, TYPE_OR_VALUES).
        '''
        _, v = s.split(' ', 1)
        v = v.strip()

        # Verify the general structure of declaration
        m = _RE_ATTRIBUTE.match(v)
        if not m:
            raise BadAttributeFormat()

        # Extracts the raw name and type
        name, type_ = m.groups()

        # Extracts the final name
        name = str(name.strip('"\''))

        # Extracts the final type
        if _RE_TYPE_NOMINAL.match(type_):
            # If follows the nominal structure, parse with csv reader.
            values = next(csv.reader([type_.strip('{} ')]))
            values = [str(v_.strip(' ').strip('"\'')) for v_ in values]
            type_ = values

        else:
            # If not nominal, verify the type name
            type_ = str(type_).upper()
            if type_ not in ['NUMERIC', 'REAL', 'INTEGER', 'STRING']:
                raise BadAttributeType()

        return (name, type_)

    def _decode_data(self, s):
        '''(INTERNAL) Decodes a line of data.

        Data instances follow the csv format, i.e, attribute values are
        delimited by commas. After converted from csv, this method uses the
        ``_conversors`` list to convert each value. Obviously, the values must
        follow the same order then their respective attributes.

        This method must receive a normalized string, i.e., a string without
        padding, including the "\r\n" characters.

        :param s: a normalized string.
        :return: a list with values.
        '''
        values = next(csv.reader([s.strip(' ')]))

        if len(values) != len(self._conversors):
            raise BadDataFormat()

        values = [self._conversors[i](values[i]) for i in range(len(values))]
        return values

    def _decode(self, s):
        '''Do the job the ``encode``.'''

        # If string, convert to a list of lines
        if isinstance(s, str):
            s = s.strip('\r\n ').replace('\r\n', '\n').split('\n')

        # Create the return object
        obj = {
            u'description': u'',
            u'relation': u'',
            u'attributes': [],
            u'data': []
        }

        # Read all lines
        STATE = _TK_DESCRIPTION
        for row in s:
            self._current_line += 1
            # Ignore empty lines
            row = row.strip(' \r\n')
            if not row: continue

            u_row = row.upper()

            # DESCRIPTION -----------------------------------------------------
            if u_row.startswith(_TK_DESCRIPTION) and STATE == _TK_DESCRIPTION:
                obj['description'] += self._decode_comment(row) + '\n'
            # -----------------------------------------------------------------

            # RELATION --------------------------------------------------------
            elif u_row.startswith(_TK_RELATION):
                if STATE != _TK_DESCRIPTION:
                    raise BadLayout()

                STATE = _TK_RELATION
                obj['relation'] = self._decode_relation(row)
            # -----------------------------------------------------------------

            # ATTRIBUTE -------------------------------------------------------
            elif u_row.startswith(_TK_ATTRIBUTE):
                if STATE != _TK_RELATION and STATE != _TK_ATTRIBUTE:
                    raise BadLayout()

                STATE = _TK_ATTRIBUTE

                attr = self._decode_attribute(row)
                obj['attributes'].append(attr)

                if isinstance(attr[1], (list, tuple)):
                    conversor = Conversor('NOMINAL', attr[1])
                else:
                    conversor = Conversor(attr[1])

                self._conversors.append(conversor)
            # -----------------------------------------------------------------

            # DATA ------------------------------------------------------------
            elif u_row.startswith(_TK_DATA):
                if STATE != _TK_ATTRIBUTE:
                    raise BadLayout()

                STATE = _TK_DATA
            # -----------------------------------------------------------------

            # COMMENT ---------------------------------------------------------
            elif u_row.startswith(_TK_COMMENT):
                pass
            # -----------------------------------------------------------------

            # DATA INSTANCES --------------------------------------------------
            elif STATE == _TK_DATA:
                obj['data'].append(self._decode_data(row))
            # -----------------------------------------------------------------

            # UNKNOWN INFORMATION ---------------------------------------------
            else:
                raise BadLayout()
            # -----------------------------------------------------------------

        if obj['description'].endswith('\n'):
            obj['description'] = obj['description'][:-1]

        return obj

    def decode(self, s):
        '''Returns the Python representation of a given ARFF file.

        When a file object is passed as an argument, this method read lines
        iteratively, avoiding to load unnecessary information to the memory.

        :param s: a string or file object with the ARFF file.
        '''
        try:
            return self._decode(s)
        except ArffException as e:
            # print e
            e.line = self._current_line
            raise e

#Esta clase, así como sus métodos son la readaptación de un módulo para poder leer los ficheros arff


class ArffEncoder(object):
    '''An ARFF encoder.'''

    def _encode_comment(self, s=''):
        '''(INTERNAL) Encodes a comment line.

        Comments are single line strings starting, obligatorily, with the ``%``
        character, and can have any symbol, including whitespaces or special
        characters.

        If ``s`` is None, this method will simply return an empty comment.

        :param s: (OPTIONAL) string.
        :return: a string with the encoded comment line.
        '''
        return u'%s %s'%(_TK_COMMENT, s)

    def _encode_relation(self, name):
        '''(INTERNAL) Decodes a relation line.

        The relation declaration is a line with the format ``@RELATION
        <relation-name>``, where ``relation-name`` is a string.

        :param name: a string.
        :return: a string with the encoded relation declaration.
        '''
        if ' ' in name:
            name = '"%s"'%name

        return u'%s %s'%(_TK_RELATION, name)

    def _encode_attribute(self, name, type_):
        '''(INTERNAL) Encodes an attribute line.

        The attribute follow the template::

             @attribute <attribute-name> <datatype>

        where ``attribute-name`` is a string, and ``datatype`` can be:

        - Numerical attributes as ``NUMERIC``, ``INTEGER`` or ``REAL``.
        - Strings as ``STRING``.
        - Dates (NOT IMPLEMENTED).
        - Nominal attributes with format:

            {<nominal-name1>, <nominal-name2>, <nominal-name3>, ...}

        This method must receive a the name of the attribute and its type, if
        the attribute type is nominal, ``type`` must be a list of values.

        :param name: a string.
        :param type_: a string or a list of string.
        :return: a string with the encoded attribute declaration.
        '''
        if ' ' in name:
            name = '"%s"'%name

        if isinstance(type_, (tuple, list)):
            type_ = [u'"%s"'%t if ' ' in t else u'%s'%t for t in type_]
            type_ = u'{%s}'%(u', '.join(type_))

        return u'%s %s %s'%(_TK_ATTRIBUTE, name, type_)

    def _encode_data(self, data):
        '''(INTERNAL) Encodes a line of data.

        Data instances follow the csv format, i.e, attribute values are
        delimited by commas. After converted from csv.

        :param data: a list of values.
        :return: a string with the encoded data line.
        '''
        new_data = []
        for v in data:
            s = str(v)
            for escape_char in _ESCAPE_DCT:
                if escape_char in s:
                    s = encode_string(s)
                    break
            new_data.append(s)

        return u','.join(new_data)

    def encode(self, obj):
        '''Encodes a given object to an ARFF file.

        :param obj: the object containing the ARFF information.
        :return: the ARFF file as an unicode string.
        '''
        data = [row for row in self.iter_encode(obj)]

        return u'\n'.join(data)

    def iter_encode(self, obj):
        '''The iterative version of `arff.ArffEncoder.encode`.

        This encodes iteratively a given object and return, one-by-one, the
        lines of the ARFF file.

        :param obj: the object containing the ARFF information.
        :return: (yields) the ARFF file as unicode strings.
        '''
        # DESCRIPTION
        if obj.get('description', None):
            for row in obj['description'].split('\n'):
                yield self._encode_comment(row)

        # RELATION
        if not obj.get('relation'):
            raise BadObject('Relation name not found or with invalid value.')

        yield self._encode_relation(obj['relation'])
        yield u''

        # ATTRIBUTES
        if not obj.get('attributes'):
            raise BadObject('Attributes not found.')

        for attr in obj['attributes']:
            # Verify for bad object format
            if not isinstance(attr, (tuple, list)) or \
               len(attr) != 2 or \
               not isinstance(attr[0], str):
                raise BadObject('Invalid attribute declaration "%s"'%str(attr))

            if isinstance(attr[1], str):
                # Verify for invalid types
                if attr[1] not in _SIMPLE_TYPES:
                    raise BadObject('Invalid attribute type "%s"'%str(attr))

            # Verify for bad object format
            elif not isinstance(attr[1], (tuple, list)):
                raise BadObject('Invalid attribute type "%s"'%str(attr))

            yield self._encode_attribute(attr[0], attr[1])
        yield u''

        # DATA
        yield _TK_DATA
        if not obj.get('data'):
            raise BadObject('Data declaration not found.')

        for inst in obj['data']:
            yield self._encode_data(inst)

        # FILLER
        yield self._encode_comment()
        yield self._encode_comment()
        yield self._encode_comment()
# =============================================================================

# BASIC INTERFACE =============================================================
#Esta clase, así como sus métodos son la readaptación de un módulo para poder leer los ficheros arff


def load(fp):
    '''Load a file-like object containing the ARFF document and convert it into
    a Python object.

    :param fp: a file-like object.
    :return: a dictionary.
     '''
    decoder = ArffDecoder()
    return decoder.decode(fp)


def loads(s):
    '''Convert a string instance containing the ARFF document into a Python
    object.

    :param s: a string object.
    :return: a dictionary.
    '''
    decoder = ArffDecoder()
    return decoder.decode(s)


def dump(obj, fp):
    '''Serialize an object representing the ARFF document to a given file-like
    object.

    :param obj: a dictionary.
    :param fp: a file-like object.
    '''
    encoder = ArffEncoder()
    generator = encoder.iter_encode(obj)

    last_row = generator.next()
    for row in generator:
        fp.write(last_row + u'\n')
        last_row = row
    fp.write(last_row)

    return fp


def dumps(obj):
    '''Serialize an object representing the ARFF document, returning a string.

    :param obj: a dictionary.
    :return: a string with the ARFF document.
    '''
    encoder = ArffEncoder()
    return encoder.encode(obj)

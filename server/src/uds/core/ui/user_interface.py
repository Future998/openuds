# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2022 Virtual Cable S.L.U.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L.U. nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
# pylint: disable=too-many-lines
import codecs
import datetime
import time
import pickle  # nosec: safe usage
import copy
import typing
import logging
import enum
from collections import abc

import yaml
from django.utils.translation import get_language, gettext as _, gettext_noop
from django.conf import settings

from uds.core.managers import cryptoManager
from uds.core.util.decorators import deprecatedClassValue

logger = logging.getLogger(__name__)

# Old encryption key
UDSB: typing.Final[bytes] = b'udsprotect'
# New encription key, different on each installation
UDSK: typing.Final[bytes] = settings.SECRET_KEY[8:24].encode()  # UDS key, new

# Separators for fields
MULTIVALUE_FIELD: typing.Final[bytes] = b'\001'
OLD_PASSWORD_FIELD: typing.Final[bytes] = b'\004'
PASSWORD_FIELD: typing.Final[bytes] = b'\005'

FIELD_SEPARATOR: typing.Final[bytes] = b'\002'
NAME_VALUE_SEPARATOR: typing.Final[bytes] = b'\003'

SERIALIZATION_HEADER: typing.Final[bytes] = b'GUIZ'
SERIALIZATION_VERSION: typing.Final[bytes] = b'\001'


class gui:
    """
    This class contains the representations of fields needed by UDS modules and
    administation interface.

    This contains fields types, that modules uses to make a form and interact
    with users.

    The use of this provided fields are as follows:

    The Module is descendant of "BaseModule", which also is inherited from this
    class.

    At class level, we declare the fields needed to interact with the user, as
    this example:

    .. code-block:: python

       class AuthModule(Authenticator):
           # ...
           # Other initializations
           # ...
           users = gui.EditableList(label = 'Users', tooltip = 'Select users',
               order = 1, values = ['user1', 'user2', 'user3', 'user4'])
           passw = gui.Password(label='Pass', length=32, tooltip='Password',
               order = 2, required = True, defValue = '12345')
           # ...
           # more fields
           # ...

    At class instantiation, this data is extracted and processed, so the admin
    can access this form to let users
    create new instances of this module.
    """

    # Values dict type
    ValuesType = typing.Optional[typing.Dict[str, str]]

    class ChoiceType(typing.TypedDict):
        id: str
        text: str

    ValuesDictType = typing.Dict[
        str,
        typing.Union[str, bool, typing.List[str], typing.List[ChoiceType]],
    ]

    # : True string value
    TRUE: typing.ClassVar[str] = 'true'
    # : False string value
    FALSE: typing.ClassVar[str] = 'false'

    class Tab(enum.Enum):
        ADVANCED = gettext_noop('Advanced')
        PARAMETERS = gettext_noop('Parameters')
        CREDENTIALS = gettext_noop('Credentials')
        TUNNEL = gettext_noop('Tunnel')
        DISPLAY = gettext_noop('Display')
        MFA = gettext_noop('MFA')

        def __str__(self) -> str:
            return str(self.value)

    # : For backward compatibility, will be removed in future versions
    # For now, will log a warning if used
    @deprecatedClassValue('gui.Tab.ADVANCED')
    def ADVANCED_TAB(cls) -> str:
        return str(gui.Tab.ADVANCED)

    @deprecatedClassValue('gui.Tab.PARAMETERS')
    def PARAMETERS_TAB(cls) -> str:
        return str(gui.Tab.PARAMETERS)

    @deprecatedClassValue('gui.Tab.CREDENTIALS')
    def CREDENTIALS_TAB(cls) -> str:
        return str(gui.Tab.CREDENTIALS)

    @deprecatedClassValue('gui.Tab.TUNNEL')
    def TUNNEL_TAB(cls) -> str:
        return str(gui.Tab.TUNNEL)

    @deprecatedClassValue('gui.Tab.DISPLAY')
    def DISPLAY_TAB(cls) -> str:
        return str(gui.Tab.DISPLAY)

    @deprecatedClassValue('gui.Tab.MFA')
    def MFA_TAB(cls) -> str:
        return str(gui.Tab.MFA)

    # : Static Callbacks simple registry
    callbacks: typing.Dict[
        str,
        typing.Callable[[typing.Dict[str, str]], typing.List[typing.Dict[str, str]]],
    ] = {}

    @staticmethod
    def choiceItem(
        id_: typing.Union[str, int], text: typing.Union[str, int]
    ) -> 'gui.ChoiceType':
        """
        Helper method to create a single choice item.

        Args:
            id: Id of the choice to create

            text: Text to assign to the choice to create

        Returns:
            An dictionary, that is the representation of a single choice item,
            with 2 keys, 'id' and 'text'

        :note: Text can be anything, the method converts it first to text before
        assigning to dictionary
        """
        return {'id': str(id_), 'text': str(text)}

    # Helpers
    @staticmethod
    def convertToChoices(
        vals: typing.Union[
            typing.Iterable[typing.Union[str, typing.Dict[str, str]]],
            typing.Dict[str, str],
            None,
        ]
    ) -> typing.List['gui.ChoiceType']:
        """
        Helper to convert from array of strings (or dictionaries) to the same dict used in choice,
        multichoice, ..
        """
        if not vals:
            return []

        # Helper to convert an item to a dict
        def choiceFromValue(
            val: typing.Union[str, int, typing.Dict[str, str]]
        ) -> 'gui.ChoiceType':
            if isinstance(val, dict):
                if 'id' not in val or 'text' not in val:
                    raise ValueError('Invalid choice dict: {}'.format(val))
                return gui.choiceItem(val['id'], val['text'])
            # If val is not a dict, and it has not 'id' and 'text', raise an exception
            return gui.choiceItem(val, val)

        # If is a dict
        if isinstance(vals, abc.Mapping):
            return [gui.choiceItem(str(k), v) for k, v in vals.items()]

        # if single value, convert to list
        if not isinstance(vals, abc.Iterable) or isinstance(vals, str):
            vals = [vals]

        # If is an iterable
        if isinstance(vals, abc.Iterable):
            return [choiceFromValue(v) for v in vals]

        # This should never happen
        raise RuntimeError('Invalid type for convertToChoices: {}'.format(type(vals)))

    @staticmethod
    def convertToList(
        vals: typing.Union[str, int, typing.Iterable]
    ) -> typing.List[str]:
        if vals:
            if isinstance(vals, (str, int)):
                return [str(vals)]
            return [str(v) for v in vals]
        return []

    @staticmethod
    def choiceImage(
        id_: typing.Union[str, int], text: str, img: str
    ) -> typing.Dict[str, str]:
        return {'id': str(id_), 'text': str(text), 'img': img}

    @staticmethod
    def sortedChoices(choices: typing.Iterable):
        return sorted(choices, key=lambda item: item['text'].lower())

    @staticmethod
    def toBool(value: typing.Union[str, bool, int]) -> bool:
        """
        Converts the string "true" (case insensitive) to True (boolean).
        Anything else is converted to false

        Args:
            str: Str to convert to boolean

        Returns:
            True if the string is "true" (case insensitive), False else.
        """
        if value is True or str(value).lower() in [gui.TRUE, '1', 'yes']:
            return True
        return False

    @staticmethod
    def fromBool(bol: bool) -> str:
        """
        Converts a boolean to the string representation. True is converted to
        "true", False to "false".

        Args:
            bol: Boolean value (True or false) to convert

        Returns:
            "true" if bol evals to True, "false" if don't.
        """
        if bol:
            return gui.TRUE
        return gui.FALSE

    # Classes

    class InputField:
        """
        Class representing an simple input field.
        This class is not directly usable, must be used by any inherited class
        (fields all of them)
        All fields are inherited from this one

        The data managed for an input field, and their default values are:
            * length: Max length of the field. Defaults to DEFAULT_LENGTH
            * required: If this field is a MUST. defaults to false
            * label: Label used with this field. Defaults to ''
            * defvalue: Default value for the field. Defaults to '' (this is
              always an string)
            * rdonly: If the field is read only on modification. On creation,
              all fields are "writable". Defaults to False
            * order: order inside the form, defaults to 0 (if two or more fields
              has same order, the output order may be anything)
            * tooltip: Tooltip used in the form, defaults to ''
            * type: type of the input field, defaults to "text box" (TextField)

        In every single field, you must at least indicate:
            * if required or not
            * order
            * label
            * tooltip
            * defvalue  (if not required, this is optional). Alias for this field is defaultValue
            * rdonly if can't be modified once it's created. Aliases for this field is readOnly

        Any other paremeter needed is indicated in the corresponding field class.

        Also a value field is available, so you can get/set the form field value.
        This property expects always an string, no matter what kind of field it is.

        Take into account also that "value" has precedence over "defValue",
        so if you use both, the used one will be "value". This is valid for
        all form fields.
        """

        class Types(enum.Enum):
            TEXT = 'text'
            TEXT_AUTOCOMPLETE = 'text-autocomplete'
            NUMERIC = 'numeric'
            PASSWORD = 'password'  # nosec: this is not a password
            HIDDEN = 'hidden'
            CHOICE = 'choice'
            MULTI_CHOICE = 'multichoice'
            EDITABLE_LIST = 'editlist'
            CHECKBOX = 'checkbox'
            IMAGE_CHOICE = 'imgchoice'
            IMAGE = 'image'
            DATE = 'date'
            INFO = 'dummy'

            def __str__(self):
                return self.value

        # : If length of some fields are not especified, this value is used as default
        DEFAULT_LENTGH: typing.ClassVar[int] = 64

        _data: typing.Dict[str, typing.Any]

        def __init__(self, **options) -> None:
            # Added defaultValue as alias for defvalue
            self._data = {}
            if 'type' in options:
                self.type = options['type']  # set type first

            defvalue = options.get(
                'defvalue', options.get('defaultValue', options.get('defValue', ''))
            )
            if callable(defvalue):
                defvalue = defvalue()
            self._data.update(
                {
                    'length': options.get(
                        'length', gui.InputField.DEFAULT_LENTGH
                    ),  # Length is not used on some kinds of fields, but present in all anyway
                    'required': options.get('required', False),
                    'label': options.get('label', ''),
                    'defvalue': str(defvalue),
                    'rdonly': options.get(
                        'rdonly',
                        options.get('readOnly', options.get('readonly', False)),
                    ),  # This property only affects in "modify" operations
                    'order': options.get('order', 0),
                    'tooltip': options.get('tooltip', ''),
                    'value': options.get('value', defvalue),
                }
            )
            if 'tab' in options:
                self._data['tab'] = str(options.get('tab'))  # Ensure it's a string

        @property
        def type(self) -> 'Types':
            return gui.InputField.Types(self._data['type'])

        @type.setter
        def type(self, type_: Types) -> None:
            """
            Sets the type of this field.

            Args:
                type: Type to set (from constants of this class)
            """
            self._data['type'] = str(type_)

        def isType(self, type_: typing.Union[Types, str]) -> bool:
            """
            Returns true if this field is of specified type
            """
            return self._data['type'] == str(type_)

        def isSerializable(self) -> bool:
            return True

        def num(self) -> int:
            return -1

        def isTrue(self) -> bool:
            return False

        @property
        def value(self) -> typing.Any:
            """
            Obtains the stored value.
            If the stored value is None (this will only happens if value is forced to be so, by default empty value is ''),
            returns default value instead.
            This is mainly used for hidden fields, so we have correctly initialized
            """
            return (
                self._data['value']
                if self._data['value'] is not None
                else self.defValue
            )

        @value.setter
        def value(self, value: typing.Any) -> None:
            """
            Stores new value (not the default one)
            """
            self._setValue(value)

        def _setValue(self, value: typing.Any) -> None:
            """
            So we can override value setting at descendants
            """
            self._data['value'] = value

        def guiDescription(self) -> typing.Dict[str, typing.Any]:
            """
            Returns the dictionary with the description of this item.
            We copy it, cause we need to translate the label and tooltip fields
            and don't want to
            alter original values.
            """
            data = self._data.copy()
            data['label'] = _(data['label']) if data['label'] else ''
            data['tooltip'] = _(data['tooltip']) if data['tooltip'] else ''
            if 'tab' in data:
                data['tab'] = _(data['tab'])  # Translates tab name
            return data

        @property
        def defValue(self) -> typing.Any:
            """
            Returns the default value for this field
            """
            return self._data['defvalue']

        @defValue.setter
        def defValue(self, defValue: typing.Any) -> None:
            self.setDefValue(defValue)

        def setDefValue(self, defValue: typing.Any) -> None:
            """
            Sets the default value of the field·

            Args:
                defValue: Default value (string)
            """
            self._data['defvalue'] = defValue

        @property
        def label(self) -> str:
            return self._data['label']

        def serialize(self) -> str:
            """Serialize value to an string"""
            return str(self.value)

        def unserialize(self, value) -> None:
            """Unserialize value from an string"""
            self.value = value

    class TextField(InputField):
        """
        This represents a text field.

        The values of parameters are inherited from :py:class:`InputField`

        Additionally to standard parameters, the length parameter is a
        recommended one for this kind of field.

        You can specify that this is a multiline text box with **multiline**
        parameter. If it exists, and is greater than 1, indicates how much
        lines will be used to display field. (Max number is 8)

        Example usage:

           .. code-block:: python

              # Declares an text form field, with label "Host", tooltip
              # "Host name for this module", that is required,
              # with max length of 64 chars and order = 1, and is editable
              # after creation.
              host = gui.TextField(length=64, label = _('Host'), order = 1,
                  tooltip = _('Host name for this module'), required = True)

              # Declares an text form field, with label "Other",
              # tooltip "Other info", that is not required, that is not
              # required and that is not editable after creation.
              other = gui.TextField(length=64, label = _('Other'), order = 1,
                  tooltip = _('Other info'), rdonly = True)

        """

        def __init__(self, **options) -> None:
            super().__init__(**options, type=gui.InputField.Types.TEXT)
            multiline = int(options.get('multiline', 0))
            if multiline > 8:
                multiline = 8
            self._data['multiline'] = multiline

        def cleanStr(self):
            return str(self.value).strip()

    class TextAutocompleteField(TextField):
        """
        This represents a text field that holds autocomplete values.
        Values are a list of strings...
        """

        def __init__(self, **options) -> None:
            super().__init__(**options)
            # Update parent type
            self.type = gui.InputField.Types.TEXT_AUTOCOMPLETE
            # And store values in a list
            self._data['values'] = gui.convertToChoices(options.get('values', []))

        def setValues(self, values: typing.List[str]):
            """
            Set the values for this choice field
            """
            self._data['values'] = gui.convertToChoices(values)

    class NumericField(InputField):
        """
        This represents a numeric field. It apears with an spin up/down button.

        The values of parameres are inherited from :py:class:`InputField`

        Additionally to standard parameters, the length parameter indicates the
        max number of digits (0-9 values).

        Example usage:

           .. code-block:: python

              # Declares an numeric form field, with max value of 99999, label
              # "Port", that is required,
              # with tooltip "Port (usually 443)" and order 1
              num = gui.NumericField(length=5, label = _('Port'),
                  defvalue = '443', order = 1, tooltip = _('Port (usually 443)'),
                  required = True)
        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.NUMERIC)
            self._data['minValue'] = int(
                options.get('minValue', options.get('minvalue', '987654321'))
            )
            self._data['maxValue'] = int(
                options.get('maxValue', options.get('maxvalue', '987654321'))
            )

        def _setValue(self, value: typing.Any):
            # Internally stores an string
            super()._setValue(str(value))

        def num(self) -> int:
            """
            Return value as integer
            """
            try:
                v = int(self.value)
            except Exception:
                v = 0
            return v

        @property
        def int_value(self) -> int:
            return self.num()

    class DateField(InputField):
        """
        This represents a date field.

        The values of parameres are inherited from :py:class:`InputField`
        """

        def processValue(
            self, valueName: str, options: typing.Dict[str, typing.Any]
        ) -> None:
            try:
                val = options.get(valueName, None)

                if not val and valueName == 'defvalue':
                    val = datetime.date.today()
                elif isinstance(val, str):
                    val = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                elif val == datetime.date.min:
                    val = datetime.date(2000, 1, 1)
                elif val == datetime.date.max:
                    # val = datetime.date(2099, 12, 31)
                    val = datetime.date.today()
                elif not isinstance(val, datetime.date):
                    val = datetime.date.today()
            # Any error, use today
            except Exception:
                val = datetime.date.today()

            options[valueName] = val.strftime('%Y-%m-%d')

        def __init__(self, **options):
            if 'value' not in options:
                options['value'] = options['defvalue']

            for v in 'value', 'defvalue':
                self.processValue(v, options)

            super().__init__(**options, type=gui.InputField.Types.DATE)

        def date(self, min: bool = True) -> datetime.date:
            """
            Returns the date this object represents

            Args:
                min (bool, optional): If true, in case of invalid date will return "min" date, else "max". Defaults to True.

            Returns:
                datetime.date: the date that this object holds, or "min" | "max" on error
            """
            try:
                return datetime.datetime.strptime(
                    self.value, '%Y-%m-%d'
                ).date()  # ISO Format
            except Exception:
                return datetime.date.min if min else datetime.date.max

        def datetime(self, min: bool = True) -> datetime.datetime:
            """
            Returns the date this object represents

            Args:
                min (bool, optional): If true, in case of invalid date will return "min" date, else "max". Defaults to True.

            Returns:
                datetime.date: the date that this object holds, or "min" | "max" on error
            """
            try:
                return datetime.datetime.strptime(self.value, '%Y-%m-%d')  # ISO Format
            except Exception:
                return datetime.datetime.min if min else datetime.datetime.max

        def stamp(self) -> int:
            return int(
                time.mktime(
                    datetime.datetime.strptime(self.value, '%Y-%m-%d').timetuple()
                )
            )


    class PasswordField(InputField):
        """
        This represents a password field. It appears with "*" at input, so the contents is not displayed

        The values of parameres are inherited from :py:class:`InputField`

        Additionally to standard parameters, the length parameter is a recommended one for this kind of field.

        Example usage:

           .. code-block:: python

              # Declares an text form field, with label "Password",
              # tooltip "Password of the user", that is required,
              # with max length of 32 chars and order = 2, and is
              # editable after creation.
              passw = gui.PasswordField(lenth=32, label = _('Password'),
                  order = 4, tooltip = _('Password of the user'),
                  required = True)

        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.PASSWORD)

        def cleanStr(self):
            return str(self.value).strip()

    class HiddenField(InputField):
        """
        This represents a hidden field. It is not displayed to the user. It use
        is for keeping info at form needed
        by module, but not editable by user (i.e., one service can keep info
        about the parent provider in hiddens)

        The values of parameres are inherited from :py:class:`InputField`

        These are almost the same as TextFields, but they do not get displayed
        for user interaction.

        Example usage:

           .. code-block:: python

              # Declares an empty hidden field
              hidden = gui.HiddenField()


           After that, at initGui method of module, we can store a value inside
           using setDefValue as shown here:

           .. code-block:: python

              def initGui(self):
                  # always set defValue using self, cause we only want to store
                  # value for current instance
                  self.hidden.setDefValue(self.parent().serialize())

        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.HIDDEN)
            self._isSerializable: bool = options.get('serializable', '') != ''

        def isSerializable(self) -> bool:
            return self._isSerializable

    class CheckBoxField(InputField):
        """
        This represents a check box field, with values "true" and "false"

        The values of parameters are inherited from :py:class:`InputField`

        The valid values for this defvalue are: "true" and "false" (as strings)

        Example usage:

           .. code-block:: python

              # Declares an check box field, with label "Use SSL", order 3,
              # tooltip "If checked, will use a ssl connection", default value
              # unchecked (not included, so it's empty, so it's not true :-))
              ssl = gui.CheckBoxField(label = _('Use SSL'), order = 3, tooltip = _('If checked, will use a ssl connection'))

        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.CHECKBOX)

        @staticmethod
        def _checkTrue(val: typing.Union[str, bytes, bool]) -> bool:
            return val in (True, 'true', 'True', b'true', b'True', 1, '1', b'1')

        def _setValue(self, value: typing.Union[str, bytes, bool]):
            """
            Override to set value to True or False (bool)
            """
            self._data['value'] = self._checkTrue(value)

        def isTrue(self):
            """
            Checks that the value is true
            """
            return self.value in (True, 'true', 'True', b'true', b'True')

        def asBool(self) -> bool:
            """
            Returns the value as bool
            """
            return self.isTrue()

    class ChoiceField(InputField):
        """
        This represents a simple combo box with single selection.

        The values of parameters are inherited from :py:class:`InputField`

        ChoiceField needs a function to provide values inside it.

        * We specify the values via "values" option this way:

           Example:

           .. code-block:: python

              choices = gui.ChoiceField(label="choices", values=[ {'id':'1',
                  'text':'Text 1'}, {'id':'xxx', 'text':'Text 2'}])

           You can specify a multi valuated field via id-values, or a
           single-valued field via id-value

        * We can override choice values at UserInterface derived class
          constructor or initGui using setValues

        There is an extra option available for this kind of field:

           fills: This options is a dictionary that contains this fields:
              * 'callbackName' : Callback name for invocation via the specific
                 method xml-rpc. This name is a name we assign to this callback,
                 and is used to locate the method when callback is invoked from
                 admin interface.
              * 'function' : Function to execute.

                 This funtion receives one parameter, that is a dictionary with
                 all parameters (that, in time, are fields names) that we have
                 requested.

                 The expected return value for this callback is an array of
                 dictionaries with fields and values to set, as
                 example show below shows.
              * 'parameters' : Array of field names to pass back to server so
                 it can obtain the results.

                 Of course, this fields must be part of the module.

           Example:

            .. code-block:: python

               choice1 = gui.ChoiceField(label="Choice 1", values = ....,
                   fills = { 'target': 'choice2', 'callback': fncValues,
                       'parameters': ['choice1', 'name']}
                   )
               choice2 = gui.ChoiceField(label="Choice 2")

            Here is a more detailed explanation, using the VC service module as
            sample.

            .. code-block:: python

               class VCHelpers(object):
                   # ...
                   # other stuff
                   # ...
                   @staticmethod
                   def getMachines(parameters):
                       # ...initialization and other stuff...
                       if parameters['resourcePool'] != '':
                           # ... do stuff ...
                       data = [ { 'name' : 'machine', 'values' : 'xxxxxx' } ]
                       return data

               class ModuleVC(services.Service)
                  # ...
                  # stuff
                  # ...
                  resourcePool = gui.ChoiceField(
                      label=_("Resource Pool"), rdonly = False, order = 5,
                      fills = {
                          'callbackName' : 'vcFillMachinesFromResource',
                          'function' : VCHelpers.getMachines,
                          'parameters' : ['vc', 'ev', 'resourcePool']
                      },
                      tooltip = _('Resource Pool containing base machine'),
                      required = True
                  )

                  machine = gui.ChoiceField(label = _("Base Machine"), order = 6,
                      tooltip = _('Base machine for this service'), required = True )

                  vc = gui.HiddenField()
                  ev = gui.HiddenField() # ....

        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.CHOICE)
            self._data['values'] = gui.convertToChoices(options.get('values'))
            if 'fills' in options:
                # Save fnc to register as callback
                fills = options['fills']
                fnc = fills['function']
                fills.pop('function')
                self._data['fills'] = fills
                gui.callbacks[fills['callbackName']] = fnc

        def setValues(self, values: typing.List['gui.ChoiceType']):
            """
            Set the values for this choice field
            """
            self._data['values'] = values

    class ImageChoiceField(InputField):
        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.IMAGE_CHOICE)
            self._data['values'] = options.get('values', [])

        def setValues(self, values: typing.List[typing.Any]):
            """
            Set the values for this choice field
            """
            self._data['values'] = values

    class MultiChoiceField(InputField):
        """
        Multichoices are list of items that are multi-selectable.

        There is a new parameter here, not covered by InputField:
            * 'rows' to tell gui how many rows to display (the length of the
              displayable list)

        "defvalue"  is expresed as a comma separated list of ids

        This class do not have callback support, as ChoiceField does.

        The values is an array of dictionaries, in the form [ { 'id' : 'a',
        'text': b }, ... ]

        Example usage:

           .. code-block:: python

              # Declares a multiple choices field, with label "Datastores", that
              is editable, with 5 rows for displaying
              # data at most in user interface, 8th in order, that is required
              and has tooltip "Datastores where to put incrementals",
              # this field is required and has 2 selectable items: "datastore0"
              with id "0" and "datastore1" with id "1"
              datastores =  gui.MultiChoiceField(label = _("Datastores"),
                  rdonly = False, rows = 5, order = 8,
                  tooltip = _('Datastores where to put incrementals'),
                  required = True,
                  values = [ {'id': '0', 'text': 'datastore0' },
                      {'id': '1', 'text': 'datastore1' } ]
                  )
        """

        def __init__(self, **options):
            super().__init__(**options, type=gui.InputField.Types.MULTI_CHOICE)
            if options.get('values') and isinstance(options.get('values'), dict):
                options['values'] = gui.convertToChoices(options['values'])
            self._data['values'] = options.get('values', [])
            self._data['rows'] = options.get('rows', -1)

        def setValues(self, values: typing.List[typing.Any]) -> None:
            """
            Set the values for this multi choice field
            """
            self._data['values'] = gui.convertToChoices(values)

    class EditableListField(InputField):
        """
        Editables list are lists of editable elements (i.e., a list of IPs, macs,
        names, etcc) treated as simple strings with no id

        The struct used to pass values is an array of strings, i.e. ['1', '2',
        'test', 'bebito', ...]

        This list don't have "selected" items, so its defvalue field is simply
        ignored.

        We only nee to pass in "label" and, maybe, "values" to set default
        content for the list.

        Keep in mind that this is an user editable list, so the user can insert
        values and/or import values from files, so
        by default it will probably have no content at all.

        Example usage:

           .. code-block:: python

              #
              ipList = gui.EditableList(label=_('List of IPS'))

        """

        # : Constant for separating values at "value" method
        SEPARATOR = '\001'

        def __init__(self, **options) -> None:
            super().__init__(**options, type=gui.InputField.Types.EDITABLE_LIST)
            self._data['values'] = gui.convertToList(options.get('values', []))

        def _setValue(self, value):
            """
            So we can override value setting at descendants
            """
            super()._setValue(value)
            self._data['values'] = gui.convertToList(value)

    class ImageField(InputField):
        """
        Image field
        """

        def __init__(self, **options) -> None:
            super().__init__(**options, type=gui.InputField.Types.IMAGE)

    class InfoField(InputField):
        """
        Informational field (no input is done)
        """

        def __init__(self, **options) -> None:
            super().__init__(**options, type=gui.InputField.Types.INFO)


class UserInterfaceType(type):
    """
    Metaclass definition for moving the user interface descriptions to a usable
    better place. This is done this way because we will "deepcopy" these fields
    later, and update references on class 'self' to the new copy. (so everyone has a different copy)
    """

    def __new__(
        cls: typing.Type['UserInterfaceType'],
        classname: str,
        bases: typing.Tuple[type, ...],
        namespace: typing.Dict[str, typing.Any],
    ) -> 'UserInterfaceType':
        newClassDict = {}
        _gui: typing.MutableMapping[str, gui.InputField] = {}

        # Make a copy of gui fields description
        # (we will update references on class 'self' to the new copy)
        for attrName, attr in namespace.items():
            if isinstance(attr, gui.InputField):
                _gui[attrName] = attr
            newClassDict[attrName] = attr
        newClassDict['_base_gui'] = _gui
        return typing.cast(
            'UserInterfaceType', type.__new__(cls, classname, bases, newClassDict)
        )


class UserInterface(metaclass=UserInterfaceType):
    """
    This class provides the management for gui descriptions (user forms)

    Once a class is derived from this one, that class can contain Field
    Descriptions,
    that will be managed correctly.

    By default, the values passed to this class constructor are used to fill
    the gui form fields values.
    """

    # Class variable that will hold the gui fields description
    _base_gui: typing.ClassVar[typing.Dict[str, gui.InputField]]

    # instance variable that will hold the gui fields description
    # this allows us to modify the gui fields values at runtime without affecting other instances
    _gui: typing.Dict[str, gui.InputField]

    def __init__(self, values: gui.ValuesType = None) -> None:
        # : If there is an array of elements to initialize, simply try to store
        # values on form fields.

        # Generate a deep copy of inherited Gui, so each User Interface instance
        # has its own "field" set, and do not share the "fielset" with others, what
        # can be really dangerous. Till now, nothing bad happened cause there where
        # being used "serialized", but this do not have to be this way

        # Ensure "gui" points to a copy of original gui, not the original one
        # this is done to avoid modifying the original gui description

        self._gui = copy.deepcopy(self._base_gui)
        for key, val in self._gui.items():  # And refresh self references to them
            setattr(
                self, key, val
            )  # val is an InputField instance, so it is a reference to self._gui[key]

        if values is not None:
            for k, v in self._gui.items():
                if k in values:
                    v.value = values[k]
                else:
                    logger.warning('Field %s not found', k)

    def initGui(self) -> None:
        """
        This method gives the oportunity to initialize gui fields before they
        are send to administration client.
        We need this because at initialization time we probably don't have the
        data for gui.

        :note: This method is used as a "trick" to allow to modify default form
               data for services. Services are child of Service Providers, and
               will probably need data from Provider to fill initial form data.
               The rest of modules will not use this, and this only will be used
               when the user requests a new service or wants to modify existing
               one.
        :note: There is a drawback of this, and it is that there is that this
               method will modify service default data. It will run fast (probably),
               but may happen that two services of same type are requested at same
               time, and returned data will be probable a nonsense. We will take care
               of this posibility in a near version...
        """

    def valuesDict(self) -> gui.ValuesDictType:
        """
        Returns own data needed for user interaction as a dict of key-names ->
        values. The values returned must be strings.

        Example:
            we have 2 text field, first named "host" and second named "port",
            we can do something like this:

            .. code-block:: python

               return { 'host' : self.host, 'port' : self.port }

            (Just the reverse of :py:meth:`.__init__`, __init__ receives this
            dict, valuesDict must return the dict)

        Names must coincide with fields declared.

        Returns:
             Dictionary, associated with declared fields.
             Default implementation returns the values stored at the gui form
             fields declared.

        :note: By default, the provided method returns the correct values
               extracted from form fields

        """
        dic: gui.ValuesDictType = {}
        for k, v in self._gui.items():
            if v.isType(gui.InputField.Types.EDITABLE_LIST):
                dic[k] = gui.convertToList(v.value)
            elif v.isType(gui.InputField.Types.MULTI_CHOICE):
                dic[k] = gui.convertToChoices(v.value)
            else:
                dic[k] = v.value
        logger.debug('Values Dict: %s', dic)
        return dic

    def oldSerializeForm(self) -> bytes:
        """
        All values stored at form fields are serialized and returned as a single
        string
        Separating char is

        The returned string is zipped and then converted to base 64

        Note: Hidens are not serialized, they are ignored

        """

        # import inspect
        # logger.debug('Caller is : {}'.format(inspect.stack()))

        arr = []
        val: typing.Any
        for k, v in self._gui.items():
            logger.debug('serializing Key: %s/%s', k, v.value)
            if v.isType(gui.InputField.Types.HIDDEN) and v.isSerializable() is False:
                # logger.debug('Field {0} is not serializable'.format(k))
                continue
            if v.isType(gui.InputField.Types.INFO):
                # logger.debug('Field {} is a dummy field and will not be serialized')
                continue
            if v.isType(gui.InputField.Types.EDITABLE_LIST) or v.isType(
                gui.InputField.Types.MULTI_CHOICE
            ):
                # logger.debug('Serializing value {0}'.format(v.value))
                val = MULTIVALUE_FIELD + pickle.dumps(v.value, protocol=0)
            elif v.isType(gui.InfoField.Types.PASSWORD):
                val = PASSWORD_FIELD + cryptoManager().AESCrypt(
                    v.value.encode('utf8'), UDSK, True
                )
            elif v.isType(gui.InputField.Types.NUMERIC):
                val = str(int(v.num())).encode('utf8')
            elif v.isType(gui.InputField.Types.CHECKBOX):
                val = v.isTrue()
            else:
                val = v.value.encode('utf8')
            if val is True:
                val = gui.TRUE.encode('utf8')
            elif val is False:
                val = gui.FALSE.encode('utf8')

            arr.append(k.encode('utf8') + NAME_VALUE_SEPARATOR + val)
        logger.debug('Arr, >>%s<<', arr)

        return codecs.encode(FIELD_SEPARATOR.join(arr), 'zip')

    def serializeForm(
        self, serializer: typing.Optional[typing.Callable[[typing.Any], str]] = None
    ) -> bytes:
        """New form serialization

        Returns:
            bytes -- serialized form (zipped)
        """

        def serialize(value: typing.Any) -> str:
            if serializer:
                return serializer(value)
            return yaml.safe_dump(value)

        fw_converters: typing.Mapping[
            gui.InfoField.Types, typing.Callable[[gui.InputField], typing.Optional[str]]
        ] = {
            gui.InputField.Types.TEXT: lambda x: x.value,
            gui.InputField.Types.TEXT_AUTOCOMPLETE: lambda x: x.value,
            gui.InputField.Types.NUMERIC: lambda x: str(int(x.num())),
            gui.InputField.Types.PASSWORD: lambda x: (
                cryptoManager().AESCrypt(x.value.encode('utf8'), UDSK, True).decode()
            ),
            gui.InputField.Types.HIDDEN: (
                lambda x: None if not x.isSerializable() else x.value
            ),
            gui.InfoField.Types.CHOICE: lambda x: x.value,
            gui.InputField.Types.MULTI_CHOICE: lambda x: serialize(x.value),
            gui.InputField.Types.EDITABLE_LIST: lambda x: serialize(x.value),
            gui.InputField.Types.CHECKBOX: lambda x: gui.TRUE if x.isTrue() else gui.FALSE,
            gui.InputField.Types.IMAGE_CHOICE: lambda x: x.value,
            gui.InputField.Types.IMAGE: lambda x: x.value,
            gui.InputField.Types.DATE: lambda x: x.value,
            gui.InputField.Types.INFO: lambda x: None,
        }
        # Any unexpected type will raise an exception
        arr = [(k, v.type.name, fw_converters[v.type](v)) for k, v in self._gui.items() if fw_converters[v.type](v) is not None]

        return SERIALIZATION_HEADER + SERIALIZATION_VERSION + codecs.encode(
            serialize(arr).encode(),
            'zip',
        )

    def unserializeForm(
        self, values: bytes, serializer: typing.Optional[typing.Callable[[str], typing.Any]] = None
    ) -> None:
        """New form unserialization

        Arguments:
            values {bytes} -- serialized form (zipped)

        Keyword Arguments:
            serializer {typing.Optional[typing.Callable[[str], typing.Any]]} -- deserializer (default: {None})
        """

        def unserialize(value: str) -> typing.Any:
            if serializer:
                return serializer(value)
            return yaml.safe_load(value)

        if not values:
            return

        if not values.startswith(SERIALIZATION_HEADER):
            # Unserialize with old method
            self.oldUnserializeForm(values)
            return
            
        version = values[len(SERIALIZATION_HEADER) : len(SERIALIZATION_HEADER) + len(SERIALIZATION_VERSION)]

        values = codecs.decode(values[len(SERIALIZATION_HEADER) + len(SERIALIZATION_VERSION) :], 'zip')
        if not values:
            return

        arr = unserialize(values.decode())
        
        # Set all values to defaults ones
        for k in self._gui:
            if (
                self._gui[k].isType(gui.InputField.Types.HIDDEN)
                and self._gui[k].isSerializable() is False
            ):
                # logger.debug('Field {0} is not unserializable'.format(k))
                continue
            self._gui[k].value = self._gui[k].defValue

        converters: typing.Mapping[
            gui.InfoField.Types, typing.Callable[[str], typing.Any]
        ] = {
            gui.InputField.Types.TEXT: lambda x: x,
            gui.InputField.Types.TEXT_AUTOCOMPLETE: lambda x: x,
            gui.InputField.Types.NUMERIC: lambda x: int(x),
            gui.InputField.Types.PASSWORD: lambda x: (
                cryptoManager().AESDecrypt(x.encode('utf8'), UDSK, True).decode()
            ),
            gui.InputField.Types.HIDDEN: lambda x: None,
            gui.InfoField.Types.CHOICE: lambda x: x,
            gui.InputField.Types.MULTI_CHOICE: lambda x: unserialize(x),
            gui.InputField.Types.EDITABLE_LIST: lambda x: unserialize(x),
            gui.InputField.Types.CHECKBOX: lambda x: x,
            gui.InputField.Types.IMAGE_CHOICE: lambda x: x,
            gui.InputField.Types.IMAGE: lambda x: x,
            gui.InputField.Types.DATE: lambda x: x,
            gui.InputField.Types.INFO: lambda x: None,
        }

        for k, t, v in arr:
            if k not in self._gui:
                logger.warning('Field %s not found in form', k)
                continue
            if t != self._gui[k].type.name:
                logger.warning('Field %s has different type than expected', k)
                continue
            self._gui[k].value = converters[self._gui[k].type](v)

    def oldUnserializeForm(self, values: bytes) -> None:
        """
        This method unserializes the values previously obtained using
        :py:meth:`serializeForm`, and stores
        the valid values form form fileds inside its corresponding field
        """
        if not values:  # Has nothing
            return

        try:
            # Set all values to defaults ones
            for k in self._gui:
                if (
                    self._gui[k].isType(gui.InputField.Types.HIDDEN)
                    and self._gui[k].isSerializable() is False
                ):
                    # logger.debug('Field {0} is not unserializable'.format(k))
                    continue
                self._gui[k].value = self._gui[k].defValue

            values = codecs.decode(values, 'zip')
            if not values:  # Has nothing
                return

            for txt in values.split(FIELD_SEPARATOR):
                kb, v = txt.split(NAME_VALUE_SEPARATOR)
                k = kb.decode('utf8')  # Convert name to string
                if k in self._gui:
                    try:
                        if v.startswith(MULTIVALUE_FIELD):
                            val = pickle.loads(  # nosec: safe pickle, controlled
                                v[1:]
                            )  # nosec: secure pickled by us for sure
                        elif v.startswith(OLD_PASSWORD_FIELD):
                            val = cryptoManager().AESDecrypt(v[1:], UDSB, True).decode()
                        elif v.startswith(PASSWORD_FIELD):
                            val = cryptoManager().AESDecrypt(v[1:], UDSK, True).decode()
                        else:
                            val = v
                            # Ensure "legacy bytes" values are loaded correctly as unicode
                            if isinstance(val, bytes):
                                val = val.decode('utf8')
                    except Exception:
                        logger.exception('Pickling {} from {}'.format(k, self))
                        val = ''
                    self._gui[k].value = val
                # logger.debug('Value for {0}:{1}'.format(k, val))
        except Exception:
            logger.exception('Exception on unserialization on %s', self.__class__)
            # Values can contain invalid characters, so we log every single char
            # logger.info('Invalid serialization data on {0} {1}'.format(self, values.encode('hex')))

    def guiDescription(self) -> typing.List[typing.MutableMapping[str, typing.Any]]:
        """
        This simple method generates the theGui description needed by the
        administration client, so it can
        represent it at user interface and manage it.

        Args:
            obj: If any, object that will get its "initGui" invoked
                    This will only happen (not to be None) in Services.
        """
        logger.debug('Active language for theGui translation: %s', get_language())
        self.initGui()  # We give the "oportunity" to fill necesary theGui data before providing it to client

        res: typing.List[typing.MutableMapping[str, typing.Any]] = [
            {'name': key, 'gui': val.guiDescription(), 'value': ''}
            for key, val in self._gui.items()
        ]
        logger.debug('theGui description: %s', res)
        return res

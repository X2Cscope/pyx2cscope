"""This module contains the Variable class and its subclasses.

The Variable class represents a variable in the MCU data memory. It provides methods for retrieving and setting the value of the variable, as well as handling arrays of variables.

Subclasses of the Variable class define specific types of variables, such as integers or floating-point numbers, and implement the necessary methods for converting between the byte representation of the variable and its actual value.

Classes:
    - Variable: Represents a variable in the MCU data memory.
    - VariableInt8: Represents an 8-bit signed integer variable.
    - VariableUint8: Represents an 8-bit unsigned integer variable.
    - VariableInt16: Represents a 16-bit signed integer variable.
    - VariableUint16: Represents a 16-bit unsigned integer variable.
    - VariableInt32: Represents a 32-bit signed integer variable.
    - VariableUint32: Represents a 32-bit unsigned integer variable.
    - VariableInt64: Represents a 64-bit signed integer variable.
    - VariableUint64: Represents a 64-bit unsigned integer variable.
    - VariableFloat: Represents a floating-point number variable.

"""

import logging
import struct
from abc import abstractmethod
from numbers import Number
from typing import List

from mchplnet import lnet


class Variable:
    """Represents a variable in the MCU data memory."""

    def __init__(
        self, l_net: lnet, address: int, array_size: int, name: str = None
    ) -> None:
        """Initialize the Variable object.

        Args:
            l_net (LNet): LNet protocol that handles the communication with the target device.
            address (int): Address of the variable in the MCU memory.
            array_size (int): The number of elements in the array, 0 in case of a plain variable.
            name (str, optional): Name of the variable. Defaults to None.
        """
        if type(self) == Variable:  # protect super class to be initiated directly
            raise Exception("<Variable> must be subclassed.")
        super().__init__()
        self.l_net = l_net
        self.address = address
        self.name = name
        self.array_size = array_size

    def __getitem__(self, item):
        """Retrieve value regarding an indexed address from the variable's base address.

        Subclasses will handle the conversion to the real value.

        Args:
            item (int): The variable index (in case of an array). Default to zero.

        Raises:
            IndexError: If the index is outside the variable scope.

        Returns:
            the value of the variable's index position.
        """
        if abs(item) > self.array_size:
            raise IndexError("Index outside scope")
        try:
            idx = self.array_size + item if item < 0 else item
            bytes_data = self._get_value_raw(index=idx)
            return self.bytes_to_value(bytes_data)
        except Exception as e:
            logging.error(e)

    def __setitem__(self, key, value):
        """Set the value regarding an indexed address from the variable's base address.

        Args:
            key (int): the index of the variable.
            value (Number): The value to be stored in the MCU.
        """
        if abs(key) > self.array_size:
            raise IndexError("Index outside scope")
        try:
            tmp_address = self.address
            idx = self.array_size + key if key < 0 else key
            self.address = self.address + idx * self.get_width()
            self.set_value(value)
            self.address = tmp_address
        except Exception as e:
            logging.error(e)

    def __len__(self):
        """Get the number of elements on this variable.

        In case the variable is an array, we will get the array size.
        In case of a single object, we will get the value 0.

        Returns:
            int: The number of elements in the array or 0 for a single variable.
        """
        return self.array_size

    def __repr__(self):
        """String representation of the Variable.

        When printing the variable on a terminal or with str() operator, instead of printing the object and
        class attributes, the name of the variable will be printed.
        """
        return self.name

    def _get_array_values(self):
        """Retrieve all values of the array from the MCU memory.

        Returns:
            List[Number]: The list of values in the array.
        """
        chunk_data = bytearray()
        data_type = self.get_width()  # width of the array elements.
        chunk_size = self.array_size * data_type
        array_byte_size = chunk_size
        max_chunk = 253
        i = 0
        while i < array_byte_size:
            size_to_read = chunk_size if chunk_size < max_chunk else max_chunk
            data = self.l_net.get_ram_array(self.address + i, size_to_read, 1)
            chunk_data.extend(data)
            chunk_size -= max_chunk
            i += size_to_read
        # split chunk_data into data_type sized groups
        chunk_data = [
            chunk_data[j: j + data_type] for j in range(0, len(chunk_data), data_type)
        ]
        # convert bytearray to number on every element of chunk_data
        return [self.bytes_to_value(k) for k in chunk_data]

    def get_value(self):
        """Get the stored value from the MCU.

        Returns:
            Number: The stored value from the MCU.
        """
        try:
            if self.is_array():
                return self._get_array_values()
            else:
                bytes_data = self._get_value_raw()
                return self.bytes_to_value(bytes_data)
        except Exception as e:
            logging.error(e)

    def _check_value_range(self, value: Number):
        """Check if the given value is in range of min and max variable values.

        Args:
            value: the variable value

        Raises:
            ValueError: if value is outside min-max range.
        """
        min_value, max_value = self._get_min_max_values()
        if value > max_value or value < min_value:
            raise ValueError(
                f"Value = {value}: Expected in range {min_value} to {max_value}"
            )

    @abstractmethod
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Return a tuple with allowed [min, max] values.

        Returns:
            tuple[Number, Number]: The minimum and maximum allowed values.
        """

    @abstractmethod
    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to the respective variable number value.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: the variable value as a number.
        """
        pass

    def bytes_to_array(self, data: bytearray) -> List[Number]:
        """Convert a byte array to a list of numbers based on variable width.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            List[Number]: The list of numbers.
        """
        array = []
        for i in range(0, len(data), self.get_width()):
            j = i + self.get_width()
            array.append(self.bytes_to_value(data[i:j]))
        return array

    @abstractmethod
    def set_value(self, new_value: Number):
        """Set the value to be stored in the MCU.

        Args:
            new_value (Number): The value to be stored in the MCU.
        """
        pass

    @abstractmethod
    def get_width(self) -> int:
        """Get the width of the variable.

        Returns:
            int: Width of the variable.
        """
        pass

    def is_array(self):
        """Check if the variable is an array in the MCU.

        Returns:
            bool: True if the variable is an array, False otherwise.
        """
        return True if self.array_size > 0 else False

    def _get_value_raw(self, index=0) -> bytearray:
        """Ask LNet and get the raw "bytearray" value from the hardware.

        Subclasses will handle the conversion to the real value.

        Args:
            index (int): The variable index (in case of an array). Default to zero.

        Raises:
            ValueError: If the returned data length is not the expected length.

        Returns:
            bytearray: Raw data returned from LNet, must be reconstructed to the right value.
        """
        try:
            # Calculate relative address in case of array element
            address = self.address + index * self.get_width()
            # Ask LNet to get the value from the target
            bytes_data = self.l_net.get_ram(address, self.get_width())
            data_length = len(bytes_data)
            if data_length > self.get_width():  # double check validity
                raise ValueError(
                    f"Expecting only {self.get_width()} bytes from LNET, but got {data_length}"
                )
            return bytes_data
        except Exception as e:
            logging.error(e)

    def _set_value_raw(self, bytes_data: bytes, index: int = 0) -> None:
        """Set the value of a variable in the microcontroller's RAM using raw bytes.

        This method sends the raw byte data to the specified memory address in the microcontroller's RAM.
        It handles the low-level communication with the microcontroller using the LNet interface.

        Args:
            bytes_data (bytes): The raw byte data to be written to the variable's memory location.
            index (int): The variable index (in case of an array). Default to zero.

        Raises:
            Exception: If there is an error in writing the data to the microcontroller's RAM.
        """
        try:
            # Calculate relative address in case of array element
            address = self.address + index * self.get_width()
            self.l_net.put_ram(address, self.get_width(), bytes_data)
        except Exception as e:
            logging.error(f"Error setting value: {e}")

    @abstractmethod
    def is_signed(self) -> bool:
        """Abstract method to determine if the variable's data type is signed.

        Implementations of this method should return True if the variable's data type
        is a signed type (like signed integers), otherwise False.

        Returns:
            bool: True if the variable is of a signed data type, False otherwise.
        """

    @abstractmethod
    def is_integer(self) -> bool:
        """Abstract method to determine if the variable's data type is an integer.

        Implementations of this method should return True if the variable's data type
        is an integer (signed or unsigned), otherwise False for non-integer data types.

        Returns:
            bool: True if the variable is of an integer data type, False otherwise.
        """


# ------------------------------INT_8------------------------------


class VariableInt8(Variable):
    """Represents an 8-bit signed integer variable."""

    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 8-bit signed integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return -128, 127

    def is_integer(self) -> bool:
        """Override: INT8 is an integer type."""
        return True

    def is_signed(self) -> bool:
        """Override: INT8 is a signed type."""
        return True

    def get_width(self) -> int:
        """Get the width of the 8-bit signed integer.

        Returns:
            int: Width of the variable, which is 1.
        """
        return 1

    def set_value(self, value: int):
        """Set the value of the 8-bit signed integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=1, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to an 8-bit signed integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 8-bit signed integer value.
        """
        return int.from_bytes(data, "little", signed=True)


# ------------------------------ UINT_8 ------------------------------


class VariableUint8(Variable):
    """Represents an 8-bit unsigned integer variable."""

    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 8-bit unsigned integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return 0, 255

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: False, because this variable is unsigned.
        """
        return False

    def get_width(self) -> int:
        """Get the width of the 8-bit unsigned integer.

        Returns:
            int: Width of the variable, which is 1.
        """
        return 1

    def set_value(self, value: int):
        """Override: Set the value of the variable in the MCU memory.

        Checks if the value is within the allowed range and converts it to bytes representation.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=1, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to an 8-bit unsigned integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 8-bit unsigned integer value.
        """
        return int.from_bytes(data, "little", signed=False)


# ------------------------------ INT_16 ------------------------------


class VariableInt16(Variable):
    """Represents a 16-bit signed integer variable in the MCU data memory."""

    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 16-bit signed integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return -32768, 32767

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: True, because this variable is signed.
        """
        return True

    def get_width(self) -> int:
        """Get the width of the 16-bit signed integer.

        Returns:
            int: Width of the variable, which is 2.
        """
        return 2

    def set_value(self, value: int):
        """Set the value of the 16-bit signed integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=2, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 16-bit signed integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 16-bit signed integer value.
        """
        return int.from_bytes(data, "little", signed=True)


# ------------------------------ UINT_16 ------------------------------


class VariableUint16(Variable):
    """Represents a 16-bit unsigned integer variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 16-bit unsigned integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return 0, 65535

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: False, because this variable is unsigned.
        """
        return False

    def get_width(self) -> int:
        """Get the width of the 16-bit unsigned integer.

        Returns:
            int: Width of the variable, which is 2.
        """
        return 2

    def set_value(self, value: int):
        """Set the value of the 16-bit unsigned integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=2, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 16-bit unsigned integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 16-bit unsigned integer value.
        """
        return int.from_bytes(data, "little", signed=False)


# ------------------------------ INT_32 ------------------------------


class VariableInt32(Variable):
    """Represents a 32-bit signed integer variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 32-bit signed integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return -0x80000000, 0x7FFFFFFF

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: True, because this variable is signed.
        """
        return True

    def get_width(self) -> int:
        """Get the width of the 32-bit signed integer.

        Returns:
            int: Width of the variable, which is 4.
        """
        return 4

    def set_value(self, value: int):
        """Set the value of the 32-bit signed integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=4, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 32-bit signed integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 32-bit signed integer value.
        """
        return int.from_bytes(data, "little", signed=True)


# ------------------------------ UINT_32 ------------------------------


class VariableUint32(Variable):
    """Represents a 32-bit unsigned integer variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 32-bit unsigned integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return 0, 0xFFFFFFFF

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: False, because this variable is unsigned.
        """
        return False

    def get_width(self) -> int:
        """Get the width of the 32-bit unsigned integer.

        Returns:
            int: Width of the variable, which is 4.
        """
        return 4

    def set_value(self, value: int):
        """Set the value of the 32-bit unsigned integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=4, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 32-bit unsigned integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 32-bit unsigned integer value.
        """
        return int.from_bytes(data, "little", signed=False)


class VariableUint64(Variable):
    """Represents a 64-bit unsigned integer variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 64-bit unsigned integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return 0, 0xFFFFFFFFFFFFFFFF

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: False, because this variable is unsigned.
        """
        return False

    def get_width(self) -> int:
        """Get the width of the 64-bit unsigned integer.

        Returns:
            int: Width of the variable, which is 8.
        """
        return 8

    def set_value(self, value: int):
        """Set the value of the 64-bit unsigned integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            bytes_data = value.to_bytes(
                length=8, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 64-bit unsigned integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 64-bit unsigned integer value.
        """
        return int.from_bytes(data, "little", signed=False)


class VariableInt64(Variable):
    """Represents a 64-bit signed integer variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 64-bit signed integer.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return -0x8000000000000000, 0x7FFFFFFFFFFFFFFF

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: True, because this variable is an integer.
        """
        return True

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: True, because this variable is signed.
        """
        return True

    def get_width(self) -> int:
        """Get the width of the 64-bit signed integer.

        Returns:
            int: Width of the variable, which is 8.
        """
        return 8

    def set_value(self, value: int):
        """Set the value of the 64-bit signed integer.

        Args:
            value (int): The value to set.
        """
        try:
            self._check_value_range(value)
            bytes_data = value.to_bytes(
                length=8, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 64-bit signed integer.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 64-bit signed integer value.
        """
        return int.from_bytes(data, "little", signed=True)


# ------------------------------ FLOAT ------------------------------


class VariableFloat(Variable):
    """Represents a 32-bit floating point variable in the MCU data memory."""
    def _get_min_max_values(self) -> tuple[Number, Number]:
        """Get the minimum and maximum values for the 32-bit floating point.

        Returns:
            tuple[Number, Number]: The minimum and maximum values.
        """
        return -0x80000000, 0x7FFFFFFF

    def is_integer(self) -> bool:
        """Check if the variable is an integer.

        Returns:
            bool: False, because this variable is a float.
        """
        return False

    def is_signed(self) -> bool:
        """Check if the variable is signed.

        Returns:
            bool: True, because this variable is signed.
        """
        return True

    def get_width(self) -> int:
        """Get the width of the 32-bit floating point.

        Returns:
            int: Width of the variable, which is 4.
        """
        return 4

    def set_value(self, value: float):
        """Set the value of the 32-bit floating point.

        Args:
            value (float): The value to set.
        """
        try:
            float_value = float(value)
            bytes_data = bytearray(struct.pack("f", float_value))
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def bytes_to_value(self, data: bytearray) -> Number:
        """Convert the byte array to a 32-bit floating point.

        Args:
            data (bytearray): The byte array to convert.

        Returns:
            Number: The 32-bit floating point value.
        """
        return struct.unpack("f", data)[0]
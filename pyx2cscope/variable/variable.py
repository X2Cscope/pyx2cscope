import logging
import struct
from abc import abstractmethod
from numbers import Number

import mchplnet.lnet as LNet
from mchplnet.services.frame_save_parameter import ScopeChannel, ScopeTrigger


class Variable:
    """Represents a variable in the MCU data memory"""

    def __init__(self, l_net: LNet, address: int, name: str = None) -> None:
        """Initialize the Variable object.

        Args:
            l_net (LNet): LNet protocol that handles the communication with the target device.
            address (int): Address of the variable in the MCU memory.
            name (str, optional): Name of the variable. Defaults to None.
        """
        if type(self) == Variable:  # protect super class to be initiated directly
            raise Exception("<Variable> must be subclassed.")
        super().__init__()
        self.l_net = l_net
        self.address = address
        self.name = name

    def get_value(self) -> Number:
        """Get the stored value from the MCU.

        Returns:
            Number: The stored value from the MCU.
        """
        pass

    def set_value(self, new_value: Number):
        """Set the value to be stored in the MCU.

        Args:
            new_value (Number): The value to be stored in the MCU.
        """
        pass

    def _get_width(self) -> int:
        """Get the width of the variable.

        Returns:
            int: Width of the variable.
        """
        pass

    def _get_value_raw(self) -> bytearray:
        """Ask LNet and get the raw "bytearray" value from the hardware.

        Subclasses will handle the conversion to the real value.

        Raises:
            ValueError: If the returned data length is not the expected length.

        Returns:
            bytearray: Raw data returned from LNet, must be reconstructed to the right value.
        """
        try:
            # Ask LNet to get the value from the target
            bytes_data = self.l_net.get_ram(self.address, self._get_width())

            data_length = len(bytes_data)
            if data_length > self._get_width():  # double check validity
                raise ValueError(
                    f"Expecting only {self._get_width()} bytes from LNET, but got {data_length}"
                )
            return bytes_data
        except Exception as e:
            logging.error(e)

    def _set_value_raw(self, bytes_data: bytes) -> None:
        try:
            self.l_net.put_ram(self.address, self._get_width(), bytes_data)
        except Exception as e:
            logging.error(e)

    @abstractmethod
    def is_signed(self) -> bool:
        pass

    @abstractmethod
    def is_integer(self) -> bool:
        pass

    def as_channel(self) -> ScopeChannel:
        return ScopeChannel(
            name=self.name,
            source_location=self.address,
            data_type_size=self._get_width(),
            source_type=0,
            is_integer=self.is_integer(),
            is_signed=self.is_signed(),
        )

    def as_trigger(
        self,
        trigger_level: int,
        trigger_delay: int,
        trigger_edge: int,
        trigger_mode: int,
    ) -> ScopeTrigger:
        return ScopeTrigger(
            channel=self.as_channel(),
            trigger_level=trigger_level,
            trigger_delay=trigger_delay,
            trigger_edge=trigger_edge,
            trigger_mode=trigger_mode,
        )


# ------------------------------INT_8------------------------------


class Variable_int8(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return True

    def _get_width(self) -> int:
        """INT8_T width is 1"""
        return 1

    def set_value(self, value: int):
        try:
            if value > 127 or value < -128:
                raise ValueError(f"Value = {value}: Expected in range -128 to 127")

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=1, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=True
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


# ------------------------------ UINT_8 ------------------------------


class Variable_uint8(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return False

    def _get_width(self) -> int:
        """UINT8_T width is 1"""
        return 1

    def set_value(self, value: int):
        try:
            if value > 255 or value < 0:
                raise ValueError(f"Value = {value}: Expected in range 0 to 255")

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=1, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=False
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


# ------------------------------ INT_16 ------------------------------


class Variable_int16(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return True

    def _get_width(self) -> int:
        """INT16_T width is 2"""
        return 2

    def set_value(self, value: int):
        try:
            if value > 32767 or value < -32768:
                raise ValueError(f"Value = {value}: Expected in range -32768 to 32767")

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=2, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=True
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


# ------------------------------ UINT_16 ------------------------------


class Variable_uint16(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return False

    def _get_width(self) -> int:
        """UINT16_T width is 2"""
        return 2

    def set_value(self, value: int):
        try:
            if value > 65535 or value < 0:
                raise ValueError(f"Value = {value}: Expected in range 0 to 65535")

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=2, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=False
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


# ------------------------------ INT_32 ------------------------------


class Variable_int32(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return True

    def _get_width(self) -> int:
        """INT32_T width is 4"""
        return 4

    def set_value(self, value: int):
        try:
            if value > 0x7FFFFFFF or value < -0x80000000:
                raise ValueError(
                    f"Value = {value}: Expected in range -2,147,483,648 to 2,147,483,647"
                )

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=4, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=True
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


# ------------------------------ UINT_32 ------------------------------


class Variable_uint32(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return False

    def _get_width(self) -> int:
        """UINT32_T width is 4"""
        return 4

    def set_value(self, value: int):
        try:
            if value > 0xFFFFFFFF or value < 0:
                raise ValueError(
                    f"Value = {value}: Expected in range 0 to 4,294,967,295"
                )

            int_value = int(value)
            bytes_data = int_value.to_bytes(
                length=4, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            int_value = int.from_bytes(
                bytes_data, "little", signed=False
            )  # reconstruct the real value
            return int_value
        except Exception as e:
            logging.error(e)


class Variable_uint64(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return False

    def _get_width(self) -> int:
        """UINT64 width is 8"""
        return 8

    def set_value(self, value: int):
        try:
            if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
                raise ValueError(
                    f"Value = {value}: Expected in range 0 to 18,446,744,073,709,551,615"
                )

            bytes_data = value.to_bytes(
                length=8, byteorder="little", signed=False
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> int:
        try:
            bytes_data = self._get_value_raw()
            value = int.from_bytes(
                bytes_data, "little", signed=False
            )  # reconstruct the real value
            return value
        except Exception as e:
            logging.error(e)


class Variable_int64(Variable):
    def is_integer(self) -> bool:
        return True

    def is_signed(self) -> bool:
        return True

    def _get_width(self) -> int:
        """INT64 width is 8"""
        return 8

    def set_value(self, value: int):
        try:
            if value < -0x8000000000000000 or value > 0x7FFFFFFFFFFFFFFF:
                raise ValueError(
                    f"Value = {value}: Expected in range -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807"
                )

            bytes_data = value.to_bytes(
                length=8, byteorder="little", signed=True
            )  # construct the bytes representation of the value
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> int:
        try:
            bytes_data = self._get_value_raw()
            value = int.from_bytes(
                bytes_data, "little", signed=True
            )  # reconstruct the real value
            return value
        except Exception as e:
            logging.error(e)


# ------------------------------ FLOAT ------------------------------


class Variable_float(Variable):
    def is_integer(self) -> bool:
        return False

    def is_signed(self) -> bool:
        return True

    def _get_width(self) -> int:
        """FLOAT width is 4"""
        return 4

    def set_value(self, value: float):
        try:
            float_value = float(value)
            bytes_data = bytearray(struct.pack("f", float_value))
            self._set_value_raw(bytes_data)
        except Exception as e:
            logging.error(e)

    def get_value(self) -> Number:
        try:
            bytes_data = self._get_value_raw()
            float_value = struct.unpack("f", bytes_data)
            return float_value[0]
        except Exception as e:
            logging.error(e)

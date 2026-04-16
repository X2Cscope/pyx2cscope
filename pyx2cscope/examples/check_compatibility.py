"""Check whether the loaded ELF file matches the connected target.

This example connects to the target, loads variables from an ELF file, and
prints the compatibility report returned by ``check_compatibility()``.
"""

from pyx2cscope.utils import get_com_port
from pyx2cscope.x2cscope import X2CScope

x2c_scope = X2CScope(port=get_com_port())
# this test assumes you have a dsPIC33CK256MP508 connected on UART

try:
    # this should be compatible
    x2c_scope.import_variables("../../tests/data/mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")
    compatibility = x2c_scope.check_compatibility()
    print("Compatibility report:")
    for key, value in compatibility.items():
        print(f"  {key}: {value}")
    x2c_scope.disconnect()

    # this should be incompatible and generate a warning
    x2c_scope.import_variables("../../tests/data/MC_FOC_DYNO_SAME54_MCLV2.elf")
    compatibility = x2c_scope.check_compatibility()
    print("Compatibility report:")
    for key, value in compatibility.items():
        print(f"  {key}: {value}")
finally:
    x2c_scope.disconnect()



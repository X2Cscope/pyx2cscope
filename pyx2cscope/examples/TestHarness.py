import logging
import pdb
logging.basicConfig(
    level=0,
    filename="TestHarness.log",
)
logging.info("Start##################")
# from mchplnet.interfaces.factory import InterfaceFactory
# from mchplnet.interfaces.factory import InterfaceType as IType
import serial
from mchplnet.lnet import LNet

from pyx2cscope.variable.variable_factory import VariableFactory

serial_port = "COM17"  # select COM port
baud_rate = 115200
serial_connection = serial.Serial(port=serial_port, baudrate=baud_rate, timeout=0.5)
# serial_connection = InterfaceFactory.get_interface(
#     IType.SERIAL, port=serial_port, baudrate=baud_rate
# )
elf_file = r"C:\_DESKTOP\MC FG F2F Vienna\pyx2cscope-dspic33ck-48-300W\mcfg.X\dist\default\production\mcfg.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)



# Variable Creation from ELF file.

system_guardKey = variable_factory.get_variable_elf("systemData.testing.guard.key")
Overrides = variable_factory.get_variable_elf("motor.testing.overrides")
OperatingMode = variable_factory.get_variable_elf("motor.testing.operatingMode")
SquareWaveValue = variable_factory.get_variable_elf("motor.testing.sqwave.value")
SquareWaveHalfPeriod = variable_factory.get_variable_elf("motor.testing.sqwave.halfperiod")
SquareWaveIDQ_D = variable_factory.get_variable_elf("motor.testing.sqwave.idq.d")
CMDRaw_D = variable_factory.get_variable_elf("motor.idqCmdRaw.d")
CMDRaw_Q = variable_factory.get_variable_elf("motor.idqCmdRaw.q")
IDCntrl_KP = variable_factory.get_variable_elf("motor.idCtrl.kp")
IDCntrl_nKP = variable_factory.get_variable_elf("motor.idCtrl.nkp")
IDCntrl_KI = variable_factory.get_variable_elf("motor.idCtrl.ki")
IDCntrl_nKI = variable_factory.get_variable_elf("motor.idCtrl.nki")


def apply_changes_for_current_control():
    system_guardKey.set_value(53260)
    Overrides.set_value(2)
    OperatingMode.set_value(2) # current control
    SquareWaveValue.set_value(1)
    SquareWaveHalfPeriod.set_value(0.5)
def apply_changes_for_velocity_control():
    system_guardKey.set_value(53260)
    Overrides.set_value(2)
    OperatingMode.set_value(3) # Velocity control
    SquareWaveValue.set_value(1)
    SquareWaveHalfPeriod.set_value(0.5)

if __name__ == "__main__":
    pdb.set_trace()
    logging.debug("Breakpoint!!")
    logging.info("Done!##########################")
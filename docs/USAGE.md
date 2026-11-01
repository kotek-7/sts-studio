# Operating the desktop app

Choose a serial port and baud rate, then click Open and Search. Select a servo in the list. The Programming tab reads registers; the Debug tab shows feedback and sends motion commands. To try these steps without hardware, enable the demo checkbox before opening a connection.

Live is enabled by default. Moving the position slider sends a command. Disable Live to adjust the value before sending it. Motion commands and torque enable are separate operations.

Write sends to each selected servo. Sync Write sends one frame for the selection. Reg Write stores commands on the servos; Action executes registered commands on the bus, including commands registered by another application.

STOP requests torque OFF for selected and previously commanded servos. Monitoring and recording continue. It cannot interrupt a serial request already in progress, and it does not clear registered commands. Any IDs whose torque state could not be confirmed remain visible.

Sweep alternates between the start and end values. Step advances by the configured step and reverses after crossing an endpoint, so it can send a value outside the displayed start/end range. Automatic motion uses a timer; it does not wait for physical arrival.

EEPROM changes require torque OFF. Writes are read back. A restore can partially succeed: already written values are not rolled back after a later failure. ID and baud changes affect how the next connection must be opened.

The Time field and current/load values are raw device values. Their meaning depends on the servo profile. CSV preserves missing measurements rather than filling them with zero. Firmware inspection checks files only; it does not flash a servo.

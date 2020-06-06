# identify and handle hardware dependencies to pass down to drivers

have_pyusb = False

try:
    import usb.core
    try:
        usb.core.find()
        have_pyusb = True
    except usb.core.NoBackendError:
        have_pyusb = False

except ImportError:
    have_pyusb = False

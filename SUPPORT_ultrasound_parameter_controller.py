import pyUlterius


class UltraParamController(object):

    def __init__(self, ultrasound):
        self.ultrasound = ultrasound

    def toggle_freeze(self):
        self.ultrasound.toggleFreeze()

    # <editor-fold description="depth">

    def increase_depth(self):
        self.ultrasound.incParam('b-depth')
        print "increase depth"

    def decrease_depth(self):
        self.ultrasound.decParam('b-depth')
        print "decrease depth"

    def get_depth_value(self):
        val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue('b-depth', int_val.access_ref()):
            val = int_val.get()
            val /= 10.0
        return val

    # </editor-fold>

    # <editor-fold description="gain">

    def increase_gain(self):
        self.ultrasound.incParam('b-gain')
        print "increase b-mode gain"

    def decrease_gain(self):
        self.ultrasound.decParam('b-gain')
        print "decrease b-mode gain"

    def get_gain_value(self):
        val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue('b-gain', int_val.access_ref()):
            val = int_val.get()
            val = (100.0*(val+3000.0))/6000.0
        return val

    # </editor-fold>

    # <editor-fold description="frequency">

    def increase_frequency(self):
        self.ultrasound.incParam('b-freq')

    def decrease_frequency(self):
        self.ultrasound.decParam('b-freq')

    def get_frequency_value(self):
        val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue('b-freq', int_val.access_ref()):
            val = int_val.get()
            val /= 1000000.0
            val = round(val, 1)
        return val

    # </editor-fold>

    # <editor-fold description="focus">

    def increase_focus(self):

        focus_depth = self.get_param_value('focus depth')
        self.ultrasound.setParamValue('focus depth', focus_depth + 2500)

    def decrease_focus(self):

        focus_depth = self.get_param_value('focus depth')
        self.ultrasound.setParamValue('focus depth', focus_depth - 2500)

    def get_focus_value(self):

        print "get focus value"

        val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue('focus depth', int_val.access_ref()):
            val = int_val.get()
            val /= 10000.0
        return val

    # </editor-fold>

    def get_param_value(self, param):
        val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue(param, int_val.access_ref()):
            val = int_val.get()
        return val
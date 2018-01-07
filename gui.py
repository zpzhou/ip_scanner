#-------------------------------------------------------------------------------
# Name:        IP Scanner GUI
# Purpose:     Graphical User Interface for the IP scanner application
#
# Author:      Peter Zhou
#
# Created:     19-05-2017
# Copyright:   (c) PBES 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import wx
import ip_scanner
import threading


class cl_ip_scan_gui(wx.Frame):

    # enumeration class used to define return values while parsing input
    class _INPUT_STATUS(object):
        prefix = 0
        range = 1
        out_bounds = 2
        empty_field = 3
        invalid_input = 4

    _ABOUT_STR = "Scans for all functional IP addresses matching the " \
                 "specified prefix and within the specified range."

    _ERROR_STR =  "Invalid Input."

    _EMPTY_FIELD_STR = "Please input a value for each field."

    _OUT_BOUNDS_STR = "Field values must be integer values between 0 to 255"

    _EXIT_WARNING_STR = "A scan is currently in session. Do you wish to exit anyways?"

    _FINISH_STR = "Scan Completed."

    _NO_REPLY_TIME = 11

    def __init__(self):

        wx.Frame.__init__(self, None)
        self.results = list()
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.ping_index = 0
        self.total_pings = 0

        self._fn_set_menu()
        self._fn_set_header()
        self._fn_set_timer()
        self._fn_set_gauge()
        self._fn_set_results_table()
        self._fn_set_input()
        self._fn_set_ctrl_btns()

        self.panel.SetSizer(self.sizer)
        self._fn_set_frame()

    def _fn_set_menu(self):

        # Create menubar
        menubar = wx.MenuBar()

        # Create file menu to be added to menu bar
        filemenu = wx.Menu()

        # Create exit item to add to file menu
        exit_item = wx.MenuItem(filemenu, wx.ID_ANY, '&Exit Application\tCtrl+E')
        filemenu.Append(exit_item)
        self.Bind(wx.EVT_MENU, self._fn_on_exit, exit_item)

        # Create quit scan item to add to file menu
        cancel_item = wx.MenuItem(filemenu, wx.ID_ANY, '&Cancel Scan\tCtrl+Q')
        filemenu.Append(cancel_item)
        self.Bind(wx.EVT_MENU, self._fn_on_cancel, cancel_item)

        # Create help menu to be added to menu bar
        helpmenu = wx.Menu()

        # Create about item to add to help menu
        about_item = wx.MenuItem(helpmenu, wx.ID_ANY, '&About\tCtrl+A')
        helpmenu.Append(about_item)
        self.Bind(wx.EVT_MENU, self._fn_on_about, about_item)

        # Add file/help menu to menu bar and set menu bar to frame
        menubar.Append(filemenu, '&File')
        menubar.Append(helpmenu, '&Help')
        self.SetMenuBar(menubar)

    # ignores CommandEvent arg to call Close()
    def _fn_on_exit(self, e):

        # output warning dialog if scanning
        if self.cancel_btn.IsEnabled():

            flags = wx.OK | wx.CANCEL | wx.ICON_WARNING
            warning = wx.MessageDialog(None, self._EXIT_WARNING_STR, 'Exit', flags)

            if warning.ShowModal() == wx.ID_OK:

                self.Close()
        else:

            self.Close()

    # ignores CommandEvent arg to quit current scan
    def _fn_on_cancel(self, e):

        # terminate scan thread
        self.scan_thread.stop()

        # reset frame title
        self.SetTitle('IP Scanner')

        # stop timer
        self._fn_stop_timer()

        # reset progress bar
        self.ping_count = 0
        wx.CallAfter(self.gauge.SetValue, self.ping_count)

        # clear previous scan from results table
        self.results_table.DeleteAllItems()

        # unlock user input and disable cancel button
        self._fn_enable_user_input()

    # ignores CommandEvent arg to create and show a message dialog
    def _fn_on_about(self, e):

        dlog = wx.MessageDialog(None, self._ABOUT_STR, 'About', wx.CLOSE | wx.ICON_INFORMATION)
        dlog.ShowModal()

    def _fn_set_header(self):

        header = wx.StaticText(self.panel, label='IP Scanner')
        header_font = wx.Font(35, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        header.SetFont(header_font)

        header_box = wx.BoxSizer(wx.HORIZONTAL)
        header_box.Add(header)
        self.sizer.Add(header_box, flag=wx.TOP | wx.ALIGN_CENTER, border=20)

    def _fn_set_timer(self):

        # create timer
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._fn_update_time_remain, self.timer)

        # create static text to display time remaining
        self.time_remain = wx.StaticText(self.panel, label='Estimated Time:')
        self.est_time = 0

        timer_box = wx.BoxSizer(wx.HORIZONTAL)
        timer_box.Add(self.time_remain, flag=wx.ALIGN_CENTER)
        self.sizer.Add((0,90))
        self.sizer.Add(timer_box, flag=wx.ALIGN_CENTER | wx.RIGHT, border=450)

    # displays run time estimate of scan on GUI
    def fn_start_timer(self, ip_list_len):

        self.est_time = self._NO_REPLY_TIME * ip_list_len
        self.time_remain.SetLabel(self._fn_get_est_time_unit())

    def _fn_stop_timer(self):

        self.timer.Stop()
        self.est_time = 0
        self.time_remain.SetLabel('Estimated Time: {} seconds'.format(self.est_time))

    # decrements time remaining shown on GUI
    def _fn_update_time_remain(self, e):

        if self.est_time > 0:
            self.est_time -= 1
            self.time_remain.SetLabel(self._fn_get_est_time_unit())

    def _fn_get_est_time_unit(self):

        if self.est_time >= 7200:
            return 'Estimated Time: {} hours, {} minutes'.format(self.est_time/3600, self.est_time % 7200)
        elif self.est_time >= 3600:
            return 'Estimated Time: {} hour, {} minutes'.format(self.est_time/3600, self.est_time % 3600)
        elif self.est_time >= 120:
            return 'Estimated Time: {} minutes'.format(self.est_time/60)
        elif self.est_time >= 60:
            return 'Estimated Time: {} minute'.format(self.est_time/60)
        else:
            return 'Estimated Time: < 1 minute'

    def _fn_set_gauge(self):

        # gauge bar starts empty if range > 0
        self.gauge = wx.Gauge(self.panel, range=1, size=(550,25))
        gauge_box = wx.BoxSizer(wx.HORIZONTAL)

        gauge_box.Add(self.gauge, proportion=1)
        self.sizer.Add((0,10))
        self.sizer.Add(gauge_box, flag=wx.CENTRE)

    def _fn_set_results_table(self):
        self.results_table = wx.ListCtrl(self.panel, wx.ID_ANY, size=(550,200), style=wx.LC_REPORT)
        self.results_table.InsertColumn(0, 'IP Address')
        self.results_table.InsertColumn(1, 'Reply')
        self.results_table.SetColumnWidth(0, wx.LIST_AUTOSIZE)

        # set font
        results_table_font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.results_table.SetFont(results_table_font)

        # set width of IP columnn to fit length of ip address
        self.results_table.SetColumnWidth(0, 80)

        results_box = wx.BoxSizer(wx.HORIZONTAL)
        results_box.Add(self.results_table, flag=wx.CENTER)
        self.sizer.Add((0, 10))
        self.sizer.Add(results_box, flag=wx.ALIGN_CENTER)

    # set labels and text boxes for user input
    def _fn_set_input(self):

        self.sizer.Add((0, 30))
        label_box = wx.BoxSizer(wx.HORIZONTAL)
        field_box = wx.BoxSizer(wx.HORIZONTAL)

        # FIELD 3
        label_3 = wx.StaticText(self.panel, label='Octet 1')
        self.field_3 = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)

        label_box.Add(label_3, flag=wx.RIGHT, border=75)
        field_box.Add(self.field_3, proportion=1, flag= wx.RIGHT, border=25)

        # FIELD 2
        label_2 = wx.StaticText(self.panel, label='Octet 2')
        self.field_2 = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)

        label_box.Add(label_2, flag=wx.RIGHT, border=75)
        field_box.Add(self.field_2, proportion=1, flag=wx.RIGHT, border=25)

        # FIELD 1
        label_1 = wx.StaticText(self.panel, label='Octet 3')
        self.field_1 = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)

        label_box.Add(label_1, flag=wx.RIGHT, border=75)
        field_box.Add(self.field_1, proportion=1, flag=wx.RIGHT, border=25)

        # FIELD 0
        label_0 = wx.StaticText(self.panel, label='Octet 4')
        self.field_0 = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)

        label_box.Add(label_0, flag=wx.RIGHT, border=75)
        field_box.Add(self.field_0, proportion=1, flag=wx.RIGHT, border=25)

        # bind submit function to return key for each text box
        self.field_3.Bind(wx.EVT_TEXT_ENTER, self._fn_on_start)
        self.field_2.Bind(wx.EVT_TEXT_ENTER, self._fn_on_start)
        self.field_1.Bind(wx.EVT_TEXT_ENTER, self._fn_on_start)
        self.field_0.Bind(wx.EVT_TEXT_ENTER, self._fn_on_start)

        self.sizer.Add(label_box, flag=wx.ALIGN_CENTER | wx.LEFT, border=25)
        self.sizer.Add((0,10))
        self.sizer.Add(field_box, flag=wx.ALIGN_CENTER | wx.LEFT, border=25)

    # sets and adds submit/cancel button to GUI
    def _fn_set_ctrl_btns(self):

        self._fn_set_start_btn()
        self._fn_set_cancel_btn()

        # horizontal box sizer to contain both buttons
        ctrl_btn_box = wx.BoxSizer(wx.HORIZONTAL)
        ctrl_btn_box.Add(self.start_btn, flag=wx.RIGHT, border=10)
        ctrl_btn_box.Add(self.cancel_btn)

        self.sizer.Add((0,30))
        self.sizer.Add(ctrl_btn_box, flag=wx.ALIGN_CENTER)

    def _fn_set_start_btn(self):

        # submit button collects input from all four fields upon being pressed
        self.start_btn = wx.Button(self.panel, label='Start')
        self.start_btn.Bind(wx.EVT_BUTTON, self._fn_on_start)

    def _fn_set_cancel_btn(self):

        self.cancel_btn = wx.Button(self.panel, label='Cancel')
        self.cancel_btn.Bind(wx.EVT_BUTTON, self._fn_on_cancel)

        # cancel button stops a scan, is disabled at start
        self.cancel_btn.Disable()

    def _fn_on_start(self, e):

        self.prefix_list = list()
        self.range_list = list()

        # store all input to be parsed into buffer
        raw_data = [ self.field_3.GetValue(),
                     self.field_2.GetValue(),
                     self.field_1.GetValue(),
                     self.field_0.GetValue() ]

        # parse the buffer into prefix_list and range_list
        curr = self._fn_parse_input(raw_data[0])
        for i in range(1, len(raw_data)):

            next = self._fn_parse_input(raw_data[i])
            if curr == self._INPUT_STATUS.range and next == self._INPUT_STATUS.prefix:
                self._fn_on_invalid_input()

            elif next == self._INPUT_STATUS.out_bounds:
                self._fn_on_out_bounds()

            elif next == self._INPUT_STATUS.empty_field:
                self._fn_on_empty_field()

            elif next == self._INPUT_STATUS.invalid_input:
                self._fn_on_invalid_input()

            else:
                curr = next

        # clear previous scan from results table
        self.results_table.DeleteAllItems()
        self.ping_index = 0

        # Update frame title
        self.SetTitle('IP Scanner (Scanning)')

        # reset progress bar
        wx.CallAfter(self.gauge.SetValue, self.ping_index)

        # lock user input and enable cancel button
        self._fn_disable_user_input()

        # execute scan
        self.scan_thread = cl_guiThread(self.prefix_list,
                                        self.range_list,
                                        self.set_gauge_range,
                                        self.update_scan_progress,
                                        self.fn_start_timer)
        # start timer
        self.timer.Start(1000)

    def _fn_parse_input(self, string):

        string = string.split('-')
        if len(string) == 2:
            self.range_list.append((string[0], string[1]))
            return self._INPUT_STATUS.range

        elif string[0] == '':
            return self._INPUT_STATUS.empty_field

        elif int(string[0]) < 0 or int(string[0]) > 255:
            return self._INPUT_STATUS.out_bounds

        elif str.isdigit( str(string[0]) ) == False:
            return self._INPUT_STATUS.invalid_input

        else:
            self.prefix_list.append(string[0])
            return self._INPUT_STATUS.prefix

    def _fn_on_invalid_input(self):

        error = wx.MessageDialog(None, self._ERROR_STR, 'Error', wx.OK | wx.ICON_ERROR)
        error.ShowModal()

    def _fn_on_out_bounds(self):

        error = wx.MessageDialog(None, self._OUT_BOUNDS_STR, 'Out Of Bounds')
        error.ShowModal()

    def _fn_on_empty_field(self):

        error = wx.MessageDialog(None, self._EMPTY_FIELD_STR, 'Empty Field', wx.OK | wx.ICON_ERROR)
        error.ShowModal()

    def _fn_disable_user_input(self):
        # lock input fields
        self._fn_disable_fields()

        # lock submit button
        self.start_btn.Disable()

        # Enable cancel button
        self.cancel_btn.Enable()

    def _fn_enable_user_input(self):
        # unlock input fields
        self._fn_enable_fields()

        # unlock submit button
        self.start_btn.Enable()

        # Disable cancel button
        self.cancel_btn.Disable()

    def _fn_disable_fields(self):
        self.field_0.SetEditable(False)
        self.field_1.SetEditable(False)
        self.field_2.SetEditable(False)
        self.field_3.SetEditable(False)

    def _fn_enable_fields(self):
        self.field_0.SetEditable(True)
        self.field_1.SetEditable(True)
        self.field_2.SetEditable(True)
        self.field_3.SetEditable(True)

    def _fn_set_frame(self):

        self.SetTitle('IP Scanner')
        self.SetSize((700, 600))
        self.Center()
        self.Show()

    def set_gauge_range(self, n):

        self.total_pings = n
        self.gauge.SetRange(self.total_pings)

    # Updates est time remaining, gauge, and results table
    def update_scan_progress(self, result):

        # decrement time remaining by run time of failed ping
        self.est_time -= self._NO_REPLY_TIME

        # append ping result to table
        self._fn_append_results_table(result)

        # update gauge
        wx.CallAfter(self.gauge.SetValue, self.ping_index)
        print 'break 4'
        print '-----------------------------------------------------------------------------------'
        if self.ping_index == self.total_pings:
            self._fn_on_finish()

    def _fn_on_finish(self):

        fin = wx.MessageDialog(None, self._FINISH_STR, 'Done', wx.CLOSE | wx.ICON_INFORMATION)
        fin.ShowModal()

        # set frame title back to normal
        self.SetTitle('IP Scanner')

        # stop timer
        self._fn_stop_timer()

        # unlock user input and disable cancel button
        self._fn_enable_user_input()

    def _fn_append_results_table(self, result):

        print 'break 0'
        ip = result[0]
        reply = result[1]
        print 'break 1'
        # insert ip address into first column
        #---------------------------------------------------------
        wx.CallAfter(self.results_table.InsertItem,self.ping_index, ip)
        print self.ping_index
        print 'break 2'
        #---------------------------------------------------------

        # insert color coded reply into second column
        wx.CallAfter(self.results_table.SetItem, self.ping_index, 1, str(reply))
        if reply == True:
            wx.CallAfter(self.results_table.SetItemBackgroundColour, self.ping_index, wx.GREEN)
        else:
            wx.CallAfter(self.results_table.SetItemBackgroundColour, self.ping_index, wx.RED)

        self.ping_index += 1
        print 'break 3'


class cl_guiThread(threading.Thread):

    def __init__(self,
                 prefix_list,
                 range_list,
                 fn_set_gauge_range,
                 fn_update_scan_progress,
                 fn_start_timer):

        # instantiate instance of ip_scanner class to perform scan
        self.scanner = ip_scanner.cl_ip_scanner(prefix_list,
                                                      range_list,
                                                      fn_set_gauge_range,
                                                      fn_update_scan_progress,
                                                      fn_start_timer)

        # instantiate thread to start scan
        threading.Thread.__init__(self)

        # exits when main thread exits
        self.daemon = True

        # execute thread
        self.start()

    # signals all children threads to exit
    def stop(self):

        self.scanner._fn_stop_scan()

    # overload run function to update GUI progress bar
    def run(self):

        self.scanner._check_active_ips()


def main():

    app = wx.App()

    # instantiate GUI
    cl_ip_scan_gui()

    # run application
    app.MainLoop()


if __name__ == '__main__':
    main()

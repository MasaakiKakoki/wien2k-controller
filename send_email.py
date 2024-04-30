from email import message
import smtplib
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import pickle
from email.mime.text import MIMEText


class EmailFromMac:

    def __init__(self):
        self.root = tk.Tk()
        self.path = "/Users/hb_wien2k/Documents/ohwada/user_informations/user_informations.pickle"
        self.user_add_list = self.user_info_load()
        self.adds = ""
        self.panel_color = "lavender"
        self.objct_color = "lavender"

    def user_info_record(self):

        self.add_list.append(self.nadd.get())

        sor_add_list = sorted(self.add_list)

        with open(self.path, mode="wb") as info_f:
            pickle.dump(sor_add_list, info_f)

        self.user_add_list = self.user_info_load()
        self.rec_win.destroy()
        self.add_win.destroy()
        self.add_panel()

    def user_info_load(self):
        with open(self.path, mode="rb") as info_f:
            data = pickle.load(info_f)
            return data

    def del_info(self):
        with open(self.path, mode="rb") as load_f:
            l = pickle.load(load_f)
            for v in self.add_del:
                l.remove(v)

        with open(self.path, mode="wb") as info_f:
            pickle.dump(l, info_f)

        self.user_add_list = self.user_info_load()
        self.del_win.destroy()
        self.add_win.destroy()
        self.add_panel()

    def info_panel(self):
        self.root.geometry("250x80")
        self.root.title("User informations Window")
        self.root.configure(bg=self.panel_color)

        lbl_add = ttk.Label(text="Email Address", background=self.objct_color)
        lbl_add.grid(column=0, row=0, sticky=tk.S)

        self.add = tk.StringVar()
        add_txt = ttk.Entry(textvariable=self.add, width=10, background=self.objct_color)
        add_txt.insert(tk.END, self.adds)
        add_txt.grid(column=0, row=1, padx=10, ipadx=10, sticky=tk.W + tk.E)
        lbl_dom = ttk.Label(text="@hiroshima-u.ac.jp", background=self.objct_color)
        lbl_dom.grid(column=1, row=1, sticky=tk.W)

        self.btn_add = ttk.Button(text="Address book", command=lambda: self.add_panel(), width=10)
        self.btn_add.grid(column=1, row=0, sticky=tk.E + tk.W)

        self.btn_sta = ttk.Button(text="Start program", command=lambda: self.run(), width=10)
        self.btn_sta.grid(column=0, columnspan=2, row=3, sticky=tk.E + tk.W)

        self.root.mainloop()

    def record_panel(self):
        self.rec_win = tk.Toplevel(master=self.root)
        self.rec_win.title("Record Informations Window")

        lbl1 = ttk.Label(self.rec_win, text="Input your address.\nNo domain.")
        lbl1.grid(column=0, row=0, sticky=tk.E + tk.W)

        self.nadd = tk.StringVar()
        nadd_txt = ttk.Entry(self.rec_win, textvariable=self.nadd, width=15, background=self.objct_color)
        nadd_txt.grid(column=0, row=1)

        button_rec = ttk.Button(self.rec_win, text='Record', command=lambda: self.user_info_record())
        button_rec.grid(column=0, row=2, sticky=tk.S)

    def add_panel(self):
        self.add_win = tk.Toplevel(master=self.root)
        self.add_win.title("Select Address Window")

        lbl_add = ttk.Label(self.add_win, text="Select your Address")
        lbl_add.grid(column=0, row=0, sticky=tk.S)

        self.add_list = self.user_add_list
        list_value = tk.StringVar()
        list_value.set(self.add_list)

        # リストボックスの作成
        self.listbox = tk.Listbox(self.add_win, height=4, listvariable=list_value, selectmode="multiple")
        self.listbox.grid(column=0, row=1, sticky=tk.S)

        button_sel = ttk.Button(self.add_win, text='Set', command=lambda: self.select_add())
        button_sel.grid(column=0, row=3, sticky=tk.S)

        button_del = ttk.Button(self.add_win, text='Delete', command=lambda: self.delete_panel())
        button_del.grid(column=0, row=5, sticky=tk.S)

        button_rec = ttk.Button(self.add_win, text='Record', command=lambda: self.record_panel())
        button_rec.grid(column=0, row=4, sticky=tk.S)

    def select_add(self):
        self.add_sel_list = []  # 選ばれたアドレスリスト
        addi_list = self.listbox.curselection()  # 選ばれたアドレスのインデックス
        for i in addi_list:
            self.add_sel_list.append(self.user_add_list[i])

        self.adds = ";".join(self.add_sel_list)

        self.add_win.destroy()
        self.info_panel()

    def delete_panel(self):
        self.del_win = tk.Toplevel(master=self.root)

        lbl1 = ttk.Label(self.del_win, text="Do you want to delete these?")
        lbl1.grid(column=0, columnspan=2, row=0)

        self.addi = self.listbox.curselection()
        n = 0
        self.add_del = []
        for i in self.addi:
            self.add_del.append(self.add_list[i])
            lbl_add = ttk.Label(self.del_win, text="Address : {}@...".format(self.add_del[n]))
            lbl_add.grid(column=0, columnspan=2, row=1 + n, sticky=tk.E + tk.W)
            n += 1

        button_yes = ttk.Button(self.del_win, text='Yes', command=lambda: self.del_info())
        button_yes.grid(column=0, row=3, sticky=tk.S)

        button_no = ttk.Button(self.del_win, text='No', command=lambda: self.del_win.destroy())
        button_no.grid(column=1, row=3, sticky=tk.S)

    def get_info(self):
        self.add_got = self.add.get() + "@hiroshima-u.ac.jp"

        if self.add_got != "":
            self.btn_add["text"] = "Change Address"
            self.btn_sta["state"] = tk.NORMAL

    def run(self):
        self.adds = self.add.get()
        self.get_adds = self.adds.split(";")
        self.get_adds = list(map(lambda a: a + "@hiroshima-u.ac.jp", self.get_adds))
        self.root.destroy()

        self.start = datetime.now()

    def set_email(self, add, error, emsg=None):
        self.end = datetime.now()
        time = self.end - self.start
        if error == 0:
            comment = """
                Python said that \"The program was completed!!\" 
                The program took {0}. 
                """.format(time)
        elif error == 1:
            comment = """
                Python said that \"The program was error stop!!\" 
                Error message is \n \"{0}\". 
                """.format(emsg)

        # メッセージ内容
        msg = message.EmailMessage()
        msg = MIMEText(comment)
        msg['Subject'] = 'Notice from your Python program!'
        msg['From'] = "hb.wien2k@gmail.com"
        msg['To'] = add

        # サーバとのやり取り
        smtpobj = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        smtpobj.login(msg['From'], "hikaribussei")
        smtpobj.sendmail(msg['From'], msg['To'], msg.as_string())
        smtpobj.close()

        print(f"Send email to {self.add}")

    def send(self, func):
        try:
            func
        except Exception as e:
            for a in self.get_adds:
                self.set_email(a, error=1, emsg=e)
        else:
            for a in self.get_adds:
                self.set_email(a, error=0)

if __name__ == "__main__":
    email = EmailFromMac()
    email.info_panel()
    # email.send(f)
#from distutils.log import error
#from pyrfc3339 import generate
import eco
import tkinter as tk
import numpy as np
from tkinter import messagebox
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)


settings = {
    "Other" : {
        "ask_to_quit": False
    },
    "Appearance" : {
        "locale" : '',
        "color" : 'black',
        "border_color" : "#99ee66",
        "border_thickness" : 1,
        "background_color" : "white",
        "frame_background_color" : "white",
        "button_color" : 'white',
        "button_background_color" : "green",
        "button_color_hover" : 'gray',
        "button_background_color_hover" : "yellow"
    }
}

class Pane():
    def __init__(self, objects, title, prefix=''):

        #graphs = ["GDP", "Inequality Coefficient", "Inequality (Lorenz)"]
        p = tk.Toplevel(root)
        p.title(title)
        main = tk.Frame(p)
        labels = []
        w = tk.Listbox(main, width=50)

        i = 0
        for o in objects: #TODO: make function refer to specific graph
            labels.append(o.to_string()) #command=lambda k=k:show_data(society, k)))
            i+=1
        
        i = 0
        for label in labels:
            w.insert(i, label)
            try:
                if objects[i].highlight:
                    w.itemconfig(i, background='grey')
            except AttributeError:
                pass
            i+=1

        button1 = PaneButton(main, "Open in a New Window", w, objects) 
        #button1.set_state("disabled")
        main.pack()
        w.pack()
        button1.pack()
        p.protocol("WM_DELETE_WINDOW", lambda:close_popup(p))

class PaneButton(Pane):
    def __init__(self, frame, text, listbox, objects):
        self.objects = objects
        self.listbox = listbox
        self.button = tk.Button(frame, text=text,
            background=settings["Appearance"]["button_background_color"],
            foreground=settings["Appearance"]["button_color"],
            activebackground=settings["Appearance"]["button_background_color_hover"],
            activeforeground=settings["Appearance"]["button_color_hover"],
            command=lambda:self.show(listbox.curselection())) #listbox.get(tk.ANCHOR)
    def pack(self):
        self.button.pack()
    def set_state(self, state):
        self.button["state"] = state
    def show(self, curselection, prefix=''):
        #show either a data display of a new pane
        try:
            index = curselection[0]
        except IndexError:
            return #nothing was selected
        if type(self.objects[index]).__name__ == "Data":
            # new DataDisplay()
            show_data(self.objects[index], 
                self.listbox.get(tk.ANCHOR)) #this affects the global open_data_displays
        else:
            Pane(self.objects[index].display_objects, self.objects[index].name)

class ParameterPane(Pane):
    def __init__(self, pane_parameters, title, information_on="credit_score"):
        p = tk.Toplevel(root)
        p.title(title)
        main = tk.Frame(p)
        info_frame = tk.Frame(main)
        param_frame = tk.Frame(main)
        information_lbls = []
        information = self.update_information()

        for k,v in information.items():
            information_lbls.append(tk.Label(info_frame, text=(snake_to_title(k)+str(v))))

        tkwidgets = []
        values = []
        for k,v in pane_parameters.items():
            values.append(v)
            tkwidgets.append(
                (tk.Label(param_frame, text=snake_to_title(k)),
                EntryWithPlaceholder(master=param_frame, placeholder=v))
            )


        apply_btn = ParameterPaneButton(main, "Apply", values) 
        #reset_btn = ParameterPaneButton(main, "Reset") #TODO: have a default

        main.pack()
        info_frame.pack()
        for lbl in information_lbls:
            lbl.pack(anchor="w")
        param_frame.pack()
        for i in range(len(tkwidgets)):
            tkwidgets[i][0].grid(column=0, row=i, sticky="e")
            tk.Label(param_frame, text=":").grid(column=1, row=i)
            tkwidgets[i][1].grid(column=2, row=i)

        apply_btn.pack()

        p.protocol("WM_DELETE_WINDOW", lambda:close_popup(p))

    def update_information(self):
        credit_info = {
            "average_credit_score: ":str(society.average_credit_score),
            "credit_risk: ":str(society.credit_risk),
            "faith_in_credit_score: ":str(society.faith_in_credit_score)
        }
        return credit_info #TODO: make this apply to information in general

class ParameterPaneButton(ParameterPane):
    def __init__(self, frame, text, params):
        key_value_pair = params
        self.button = tk.Button(frame, text=text,
            background=settings["Appearance"]["button_background_color"],
            foreground=settings["Appearance"]["button_color"],
            activebackground=settings["Appearance"]["button_background_color_hover"],
            activeforeground=settings["Appearance"]["button_color_hover"],
            command=lambda:self.apply(key_value_pair)) #listbox.get(tk.ANCHOR)
    def pack(self):
        self.button.pack()
    def apply(self, key_value_pair):
        for k, v in key_value_pair():
            self.params[k] = v
    def reset(self): #TODO: have a default
        pass

class EntryWithPlaceholder(tk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='black'):
        super().__init__(master)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_placeholder()

class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, title="", text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 360   #pixels
        self.widget = widget
        self.title = title
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget, background="#ffffff")
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        if self.title:
            title_label = tk.Label(self.tw, text=self.title, justify='left',
                           background="#ffffff",
                           wraplength = self.wraplength, font='Helvetica 12 bold')
            title_label.pack(ipadx=1)
        text_label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff",
                       wraplength = self.wraplength)

        text_label.pack(ipadx=1, side="bottom")

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class DataDisplay():
    def __init__(self, data_obj, name, prefix=''):
        self.data_obj = data_obj
        self.name = name

        self.prefix = prefix

    def open_in_window(self):
        self.window = tk.Toplevel(root) #root is global probly
        self.window.protocol("WM_DELETE_WINDOW", lambda:self.close())
        self.window.title(self.name)
        self.render()

    def render(self):
        pass

    def to_string(self):
        return self.name


class Graph(DataDisplay):
    def __init__(self, data_obj, name, prefix=''):
        super().__init__(self, data_obj, name)
        self.data_obj = data_obj
        self.arr = data_obj.data
        self.figure, self.ax = plt.subplots(figsize=[6,6])
        self.plot_figure()
    def plot_figure(self):
        ## if no x_value, just make the graph even dist
        if self.data_obj.x_value:
            x = self.arr[0]
            y = self.arr[1]
        else:
            x = np.arange(self.arr.size)/(self.arr.size-1)
            y = self.arr

        self.ax.scatter(x, y, marker='.', color='blue', s=5)
        ## line plot of equality
        if self.data_obj.line != None:
            
            slope = self.data_obj.line
            x_line = np.linspace(min(x),max(x),2)


            if self.data_obj.x_value:
                median = [np.median(x), np.median(y)]
                at = slope*median[0]
                b = median[1]-at
            else:
                b = 0

            y_line = slope * x_line + b

            self.ax.plot(x_line, y_line, color='k')

    def render(self):

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.window)
        self.canvas.draw()
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().pack()
        self.add_toolbar()
    def add_toolbar(self):
        # creating the Matplotlib toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, self.window)
        toolbar.update()
        # placing the toolbar on the Tkinter window
        self.canvas.get_tk_widget().pack()
    def update(self):
        #call the clear method on your axes
        self.ax.clear()
        #plot the new data
        self.arr = self.data_obj.data
        self.plot_figure()
        #call the draw method on your canvas
        self.canvas.draw()
    def close(self):
        close_popup(self.window)
        plt.close(self.figure)
        open_data_displays.remove(self)

class Table(DataDisplay):
    def __init__(self, data_obj, name, prefix=''):
        super().__init__(self, data_obj, name)
        self.data_obj = data_obj
        self.generate_table()

    def generate_table(self):
        self.column_names = []
        column_ids = []
        i = 0
        for col in self.data_obj.properties["table"]["columns"]:
            column_ids.append("c"+str(i+1))
            self.column_names.append(col)
            i += 1
        self.column_ids = tuple(column_ids)
        longest_column = 0
        rows = []
        for i in range(len(self.data_obj.data)): #tables dont use numpy
            col = []
            c = 0
            for j in range(len(self.data_obj.data[i])):
                try: #if index in range
                    item = self.data_obj.data[i][j]
                    try: #if object, use to_string()
                        col.append(item.to_string())
                    except AttributeError:
                        col.append(item)
                except IndexError:
                    break #creates "ragged" arrays
                c += 1
            rows.append(col)
            if c > longest_column:
                longest_column = c
        self.table = rows
        self.longest_column = longest_column

    def render(self):
        table_frame = tk.Frame(self.window)

        tree = ttk.Treeview(table_frame, column=self.column_ids, show='headings', selectmode='browse')

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        vsb.pack(side='right', fill='both') #place(x=30+200+2, y=95, height=200+20)
        tree.configure(yscrollcommand=vsb.set)

        for i in range(len(self.column_names)):
            tree.column("# "+str(i+1), anchor=tk.CENTER)
            tree.heading("# "+str(i+1), text=self.column_names[i])

        for i in range(self.longest_column):
            tree.insert('', 'end', text=str(i+1), values=[x[i] for x in self.table]) #TODO: add try except for index error

        table_frame.pack(padx=19, fill='both', expand="yes")
        tree.pack(fill='both', expand="yes")

    def update(self):
        pass

    def close(self):
        close_popup(self.window)
        open_data_displays.remove(self)

class Stats(DataDisplay):
    def __init__(self, data_obj, name, prefix=''):
        super().__init__(self, data_obj, name)
        self.data_obj = data_obj

    def render(self):
        print(self.data_obj.data)
        for k, v in self.data_obj.data.items():
            if type(v) is list:
                print(k + " is list")
            elif type(v) is int:
                print(k + " is int")
            elif type(v) is str:
                print(k + " is string")
            elif type(v) is bool:
                print(k + " is bool")

    def update(self):
        pass

    def close(self):
        close_popup(self.window)
        open_data_displays.remove(self)



def next_day(society):
    eco.elapse_one_day(society)
    day.set("Day: "+str(society.day))
    if society.last_gdp == None:
        gdp.set("GDP: Not Calculated")
    else:
        gdp.set("GDP: "+eco.format_currency(society.last_gdp))
    mc.set("MC: "+eco.format_currency(society.mc))
    ineq.set("\u2260: "+str(round(society.inequality, 4)))
    #print(open_data_displays)
    for g in open_data_displays:
        g.update()

def show_data(data_obj, graph_name, prefix=''):
    # g = DataDisplay(data_obj, graph_name, prefix=prefix)

    if data_obj.display == "graph": #TODO: make these child classes
        g = Graph(data_obj, graph_name, prefix=prefix)    
    elif data_obj.display == "table":
        g = Table(data_obj, graph_name, prefix=prefix)
    elif data_obj.display == "stats":
        g = Stats(data_obj, graph_name, prefix=prefix)
   
    g.open_in_window()
    open_data_displays.append(g)
    vis_buttons[0]["state"] = "normal"

def close_popup(popup):
    popup.destroy()

def on_closing():
    do_quit = True
    if settings["Other"]["ask_to_quit"] == True:
        do_quit = messagebox.askokcancel("Quit", "Do you really want to quit?")
    if do_quit:
        root.destroy()
        plt.close('all')
        exit()

def snake_to_title(string):
    t = string.split("_")
    title = []
    for each in t:
        title.append(each.capitalize())
    return " ".join(title)

if __name__ == "__main__":
    print("Starting program...")
    open_data_displays = []

    society = eco.Society(100, 10000000)
    day = 0

    root = tk.Tk()
    #root.geometry("800x600")
    root.title("Super Currency Issuer")

    menubar = tk.Menu(root)
    root.config(menu=menubar)

    fileMenu = tk.Menu(menubar, tearoff="off")
    menubar.add_cascade(label="File", menu=fileMenu)
    fileMenu.add_command(label="Exit", command=on_closing)

    editMenu = tk.Menu(menubar, tearoff="off")
    menubar.add_cascade(label="Edit", menu=editMenu)
    editMenu.add_command(label="Settings") #TODO: Add command

    root_frame = tk.Frame(root, 
        background=settings["Appearance"]["background_color"])

    #################################
    #
    #      CREATE DATE WIDGETS
    #
    #################################

    day = tk.StringVar()
    day.set("Day: "+str(society.day))

    date_frame = tk.Frame(root_frame, 
        highlightbackground=settings["Appearance"]["border_color"], highlightthickness=settings["Appearance"]["border_thickness"], 
        background=settings["Appearance"]["frame_background_color"])

    day_lbl = tk.Label(date_frame, textvariable=day, 
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])

    #################################
    #
    #      CREATE TIME CONTROLS
    #
    #################################

    time_frame = tk.Frame(root_frame,
        highlightbackground=settings["Appearance"]["border_color"], highlightthickness=settings["Appearance"]["border_thickness"], 
        padx= 5, pady=5, background=settings["Appearance"]["frame_background_color"])
    time_btn = tk.Button(time_frame, text="Next Day", 
        background=settings["Appearance"]["button_background_color"],
        foreground=settings["Appearance"]["button_color"],
        activebackground=settings["Appearance"]["button_background_color_hover"],
        activeforeground=settings["Appearance"]["button_color_hover"],
        command=lambda:next_day(society))

    #################################
    #
    #      CREATE METRICS WIDGETS
    #
    #################################

    gdp = tk.StringVar()
    mc = tk.StringVar()
    ineq = tk.StringVar()
    
    if society.last_gdp == None:
        gdp.set("GDP: Not Calculated")
    else:
        gdp.set("GDP: "+eco.format_currency(society.last_gdp))
    mc.set("MC: $"+eco.format_currency(society.mc))
    ineq.set("\u2260: "+eco.format_currency(society.inequality))

    metrics_frame = tk.Frame(root_frame,
        highlightbackground=settings["Appearance"]["border_color"], highlightthickness=settings["Appearance"]["border_thickness"], 
        padx= 5, pady=5, background=settings["Appearance"]["frame_background_color"])
    gdp_lbl = tk.Label(metrics_frame, textvariable=gdp,
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])
    gdp_ttp = CreateToolTip(gdp_lbl, \
    'Gross Domestic Product (GDP) \n', \
    'The total monetary or market value of all the finished goods and services '
    'produced within a country’s borders in a specific time period. As a broad '
    'measure of overall domestic production, it functions as a comprehensive '
    'scorecard of a given country’s economic health.')
    mc_lbl = tk.Label(metrics_frame, textvariable=mc,
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])
    mc_ttp = CreateToolTip(mc_lbl, \
    'Market Cumulation \n', \
    'The value of everything available for purchase.')
    ineq_lbl = tk.Label(metrics_frame, textvariable=ineq,
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])
    ineq_ttp = CreateToolTip(ineq_lbl, \
    'Wealth Inequality \n', \
    'How unevenly income is distributed throughout a population. The less '
    'equal the distribution, the higher income inequality is.')

    #################################
    #
    #      CREATE POLICIES WIDGETS
    #
    #################################

    policies_frame = tk.Frame(root_frame,
        highlightbackground=settings["Appearance"]["border_color"], highlightthickness=settings["Appearance"]["border_thickness"], 
        padx= 5, pady=5, background=settings["Appearance"]["frame_background_color"])
    
    # CENTRAL BANK POLICIES
    
    cb_buttons = []
    credit_info = {
        "average_credit_score: ":str(society.average_credit_score),
        "credit_risk: ":str(society.credit_risk),
        "faith_in_credit_score: ":str(society.faith_in_credit_score)
    }

    central_bank_lbl = tk.Label(policies_frame, text="Central Bank Policies and Actions: ",
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])

    cb_buttons.append(
            tk.Button(policies_frame, text="Credit Score", 
                background=settings["Appearance"]["button_background_color"],
                foreground=settings["Appearance"]["button_color"],
                activebackground=settings["Appearance"]["button_background_color_hover"],
                activeforeground=settings["Appearance"]["button_color_hover"],
                command=lambda:ParameterPane(eco.preferences["credit"]["credit_score"], "Credit Score", information_on="credit_score")
        )
    )

    # LEGISLATION

    legislation_lbl = tk.Label(policies_frame, text="Legislation: ",
        background=settings["Appearance"]["frame_background_color"],
        foreground=settings["Appearance"]["color"])

    #################################
    #
    #      CREATE VISUALS WIDGETS
    #
    #################################

    vis_button_names = ["Graphs", "People", "Products", "Jobs", "Debts"]
    vis_buttons = []

    visuals_frame =tk.Frame(root_frame,
        highlightbackground=settings["Appearance"]["border_color"], highlightthickness=settings["Appearance"]["border_thickness"], 
        padx= 5, pady=5, background=settings["Appearance"]["frame_background_color"])
    
    vis_buttons.append(
            tk.Button(visuals_frame, text="Open Windows", 
                background=settings["Appearance"]["button_background_color"],
                foreground=settings["Appearance"]["button_color"],
                activebackground=settings["Appearance"]["button_background_color_hover"],
                activeforeground=settings["Appearance"]["button_color_hover"],
                state=tk.DISABLED,
                command=lambda:Pane(open_data_displays, "Open Windows")
        )
    )

    for button_name in vis_button_names:
        vis_buttons.append(
            tk.Button(visuals_frame, text=button_name, 
                background=settings["Appearance"]["button_background_color"],
                foreground=settings["Appearance"]["button_color"],
                activebackground=settings["Appearance"]["button_background_color_hover"],
                activeforeground=settings["Appearance"]["button_color_hover"],
                command=lambda button_name=button_name:Pane(society.get(button_name.lower()), button_name)
        )
    )

    graphs_frame = tk.Frame(visuals_frame, height=450, width=450)

    ########
    #
    # Pack it Up
    #
    ########

    root_frame.pack()

    date_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
    day_lbl.pack(side='left')

    time_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
    time_btn.pack()

    metrics_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5, columnspan = 2)
    gdp_lbl.pack(side='left')
    mc_lbl.pack(side='left')
    ineq_lbl.pack(side='left')

    policies_frame.grid(row=2, column=1, sticky="nsew", padx=10, pady=5)
    central_bank_lbl.pack()
    legislation_lbl.pack()

    visuals_frame.grid(row=2,column=0, rowspan=60, sticky="nsew", padx=10, pady=5)
    graphs_frame.pack()

    for b in cb_buttons:
        b.pack()
    for b in vis_buttons:
        b.pack(side="left")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

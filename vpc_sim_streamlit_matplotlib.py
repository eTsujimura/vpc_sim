import streamlit as st
import random
from matplotlib import pyplot

# Define the Slot class
class Slot():
    def __init__(self, name, active=True, maxBuffer=3, buffer=1, takt=6):
        self.name = name
        self.active = active
        self.buffer = buffer
        self.maxBuffer = maxBuffer
        self.takt = takt
        self.cnt = 0
        self.complete = 0
        self.nextSlot = None
        self.comment = ""

    def deliver(self):
        if self.active == False:
            self.comment = self.comment + "No car, "
            return False

        if self.cnt < self.takt:
            self.comment = self.comment + "Workning on, "
            return False

        if self.nextSlot.buffer >= self.nextSlot.maxBuffer:
            self.comment = self.comment + "No buffer to push, "
            return False

        self.complete += 1
        self.comment = self.comment + "Delivered, "
        self.active = False  # clear once
        self.nextSlot.buffer += 1
        return True

    def new(self):
        if self.active:
            self.comment = self.comment + "Not ready for next, "
            return False

        if self.buffer == 0:
            self.comment = self.comment + "No buffer, "
            return False

        self.buffer -= 1  # consume a buffer
        self.comment = self.comment + "Buffer became {0}, ".format(self.buffer)
        self.active = True  # back to active
        self.cnt = 0
        return True

    def countUp(self):
        self.cnt += 1
        self.comment = "Count up {0}>={1}, ".format(self.cnt, self.takt)  # reset comment
        self.deliver()
        self.new()

    def status(self):
        st.write("{0:<20}: | [Buffer] {1:>5} | [Active] {2:>3} | [complete]{3:>5} | [Cnt] {4:>3} | {5}".format(self.name, self.buffer, self.active, self.complete, self.cnt, self.comment))

# Define the Slot_branch class
class Slot_branch(Slot):
    def __init__(self, name, active=True, maxBuffer=3, buffer=1, takt=6):
        super().__init__(name, active, maxBuffer, buffer, takt)
        self.nextRepair = None  # adding repair slots

    def deliver(self):
        if self.active == False:
            self.comment = self.comment + "No car, "
            return False

        if self.cnt < self.takt:
            self.comment = self.comment + "Workning on, "
            return False

        detection = return_repairtime_x_persent(DEFECT_RATE)

        if detection==False:
            if self.nextSlot.buffer >= self.nextSlot.maxBuffer:
                self.comment = self.comment + "No buffer to push, "
                return False
            else:
                self.complete += 1
                self.comment = self.comment + "Delivered(STD), "
                self.active = False  # clear once
                self.nextSlot.buffer += 1
                return True
        else:
            self.complete += 1
            self.nextRepair.new(detection)
            self.comment = self.comment + "Sent for repair {}h, ".format(detection)
            self.active = False  # clear once
            return True

# Define the RepairSlots class
class RepairSlots():
    def __init__(self, name, repairSlots=6, out_buffer=0):
        self.name = name
        self.repairSlots = repairSlots
        self.in_buffer = [] # only for testing
        self.partsWaiting = []
        self.out_buffer = out_buffer
        self.complete = 0
        self.nextSlot = None
        self.comment = ""
        self.bays = []

    def new(self, labour):
        if return_true_x_percent(PARTS_REQURED):
            lead_time = return_repairtime_x_persent(PARTS_LEADTIME)
            self.partsWaiting.append([int(labour*60), lead_time])
            self.comment = self.comment + "sent to parts waiting, "
        elif len(self.bays) < self.repairSlots:
            self.bays.append(int(labour*60))
            self.comment = self.comment + "sent on slot, "
        else:
            self.in_buffer.append(int(labour*60))
            self.comment = self.comment + "sent to in_buffera, "

    def status(self):
        st.write("{0:<20}: | [inBuffer] {1:>5} | [parts waiting ]{2:>3} |Slots  {3} | {4} ".format(self.name, len(self.in_buffer), len(self.partsWaiting), self.bays, self.comment))

    def deliver(self):
        self.complete += 1
        if self.nextSlot.buffer >= self.nextSlot.maxBuffer:
            self.comment = self.comment + "Sent to out_buffer, "
            return False
        else:
            self.comment = self.comment + "Delivered(STD), "
            self.nextSlot.buffer += 1
            return True

    def countUp(self):
        self.comment = ""  # reset comment

        if len(self.bays) > 0:
            self.bays = [i-1 for i in self.bays]

        complete = self.bays.count(0)
        if complete > 0:
            self.comment = self.comment + "{} completed, ".format(complete)
            for i in range(complete):
                self.deliver()

        self.bays = [i for i in self.bays if i !=0]

        if len(self.bays) < self.repairSlots:
            try:
                pop = self.in_buffer.pop(0)
                self.bays.append(pop)
            except:
                pass

    def nextDay(self):
        self.partsWaiting = [[l[0], l[1]-1] for l in self.partsWaiting]

        tmp_pw = self.partsWaiting
        self.partsWaiting = []
        for l in tmp_pw:
            if l[1] <= 0:
                self.in_buffer.append(l[0])
            else:
                self.partsWaiting.append(l)

# Define the VPC class
class VPC():
    def __init__(self):
        self.time = 0
        ENTRY_CARS = int(ETA.pop()/NUMBER_OF_LINES)

        self.s01 = Slot("Entry", maxBuffer=ANNUAL_IMPORT_CARS, buffer=ENTRY_CARS, takt=TAKT_TIME)
        self.s02 = Slot("Function check", takt=TAKT_TIME)
        self.s03 = Slot("Exterior check 1", takt=TAKT_TIME)
        self.s04 = Slot("Exterior check 2", takt=TAKT_TIME)
        self.s05 = Slot_branch("Interior check", takt=TAKT_TIME)
        self.r01 = RepairSlots("Generl repair", REPAIR_BAYS)
        self.s06 = Slot("Final check", maxBuffer=ANNUAL_IMPORT_CARS+200, takt=TAKT_TIME)
        self.p01 = Slot("Parking", maxBuffer=ANNUAL_IMPORT_CARS+200, buffer=0, takt=TAKT_TIME)

        self.s01.nextSlot = self.s02
        self.s02.nextSlot = self.s03
        self.s03.nextSlot = self.s04
        self.s04.nextSlot = self.s05
        self.s05.nextSlot = self.s06
        self.s05.nextRepair = self.r01
        self.r01.nextSlot = self.s06
        self.s06.nextSlot = self.p01

    def tick(self):
        self.time += 1
        self.s01.countUp()
        self.s02.countUp()
        self.s03.countUp()
        self.s04.countUp()
        self.s05.countUp()
        self.r01.countUp()
        self.s06.countUp()

    def block_stock_status(self):
        report = "Produced from Day 1 = {} \n\n".format(self.p01.buffer*NUMBER_OF_LINES)
        report = report + "==Waiting for repair== | TTL = {} \n".format(len(self.r01.in_buffer)*NUMBER_OF_LINES)
        report = report + "\n\n"
        report = report + "==Waiting for parts== | TTL = {} \n".format(len(self.r01.partsWaiting)*NUMBER_OF_LINES)
        blocked_cars = len(self.r01.in_buffer) + len(self.r01.partsWaiting)
        inprocess_cars = (self.s01.complete - self.p01.buffer - blocked_cars)*NUMBER_OF_LINES
        blocked_cars = blocked_cars * NUMBER_OF_LINES
        report = report + "\n====== \nTTL Blocked = {0}  | TTL in-process = {1} \n".format(blocked_cars, inprocess_cars)
        report = report + "\n"
        return report

# Define helper functions
def return_true_x_percent(x):
    random_number = random.random()
    return random_number <= x/100

def return_repairtime_x_persent(dRate):
    random_number = random.random()
    if random_number <= dRate[0][0]/100:
        return False
    elif random_number <= dRate[1][0]/100:
        return dRate[0][1]
    else:
        return dRate[1][1]

# Streamlit app
st.title("VPC Simulator")

# Simulation parameters
NUMBER_OF_LINES = st.sidebar.number_input("Number of Lines", value=1)
PER_SHIFT_MAX_CLOCK = 8*60  # 8 hours
SHIFT_PER_DAY = st.sidebar.number_input("Shifts per Day", value=1)
SIMULATE_DAYS = st.sidebar.number_input("Simulate Days", value=80)
TAKT_TIME = st.sidebar.number_input("Takt Time", value=8)
REPAIR_BAYS = st.sidebar.number_input("Repair Bays", value=18)
DELTA = 1.00*SHIFT_PER_DAY
INITIAL_STOCK = st.sidebar.number_input("Initial stock", value=1000)
ETA = ([0] + [INITIAL_STOCK] + [0]*60)
ETA.reverse()
ANNUAL_IMPORT_CARS = int(sum(ETA) / NUMBER_OF_LINES + 100)
PARTS_REQURED = st.sidebar.number_input("Parts Required (%)", value=30)
FILL_RATE = st.sidebar.slider("Fill rate", 0, 100, 80, 1)  # 0 - 100
AVE_REPAIR_HOUR1 = st.sidebar.number_input("ave repair hour (small)", value=3.07)
AVE_REPAIR_HOUR2 = st.sidebar.number_input("ave repair hour (large)", value=3.07)

DEFECT_RATE = [[0, AVE_REPAIR_HOUR1], [80, AVE_REPAIR_HOUR2]]
PARTS_LEADTIME = [[0, 1], [FILL_RATE, 60]]  # Stock parts 1 days BO 60 days

# Run simulation
if st.sidebar.button("Run Simulation"):
    v = VPC()
    lastReport = "\n \u25a0\u25a0\u25a0\u25a0\u25a0\u25a0\u25a0 FINAL REPORT \u25a0\u25a0\u25a0\u25a0\u25a0\u25a0\u25a0\u25a0 \n"

    init_production = 0
    PDI_in_cnt = 0
    daily_PDI_in = []
    daily_productios = []
    dailiy_repairWaiting = []
    daily_partsWaiting = []
    daily_inprocess = []
    daily_prePDI = []

    for d in range(SIMULATE_DAYS):
        for m in range(int(PER_SHIFT_MAX_CLOCK*SHIFT_PER_DAY)+1):
            v.tick()

        try:
            arrived_cars = int(ETA.pop()/NUMBER_OF_LINES)
        except:
            arrived_cars = 0

        v.s01.buffer += arrived_cars

        cnt = v.s01.complete - PDI_in_cnt
        daily_PDI_in.append(cnt)
        PDI_in_cnt = v.s01.complete

        ttl_produced = v.p01.buffer
        daily_productios.append((ttl_produced - init_production) * NUMBER_OF_LINES)
        init_production = ttl_produced

        blocked_cars = len(v.r01.in_buffer) + len(v.r01.partsWaiting)
        daily_inprocess.append((v.s06.buffer)*NUMBER_OF_LINES)
        daily_prePDI.append((v.s01.buffer)*NUMBER_OF_LINES)
        dailiy_repairWaiting.append(len(v.r01.in_buffer)*NUMBER_OF_LINES)
        daily_partsWaiting.append(len(v.r01.partsWaiting)*NUMBER_OF_LINES)

        v.r01.nextDay()

        r = v.block_stock_status()
        lastReport = lastReport + "Daily production : \n{0}\n\n".format(daily_productios)
        lastReport = lastReport + "Daily repair waiting :\n{}\n\n".format(dailiy_repairWaiting)
        lastReport = lastReport + "Daily parts waiting :\n{}\n\n".format(daily_partsWaiting)
        lastReport = lastReport + r + "\n"

##    st.write(lastReport)

##    st.write("###### Slots status ######")
##    v.s01.status()
##    v.s02.status()
##    v.s03.status()
##    v.s04.status()
##    v.s05.status()
##    v.r01.status()
##    v.s06.status()
##    v.p01.status()

##    st.write("###### max. parts waiting######")
##    st.write(max(daily_partsWaiting))
##
##    st.write("###### max. repair waiting ######")
##    st.write(max(dailiy_repairWaiting))
##
##    st.write("###### max. buffer before final ######")
##    st.write(max(daily_inprocess))
##
##    st.write("###### max. parking ######")
    z = zip(daily_partsWaiting, dailiy_repairWaiting, daily_inprocess)
##    daily_combined = [x + y + z for (x, y, z) in z]
##    st.write(max(daily_combined))

    x = range(SIMULATE_DAYS)
    fig = pyplot.figure(figsize=(8,5))
    pyplot.subplot(3,1,1)
    pyplot.plot(x,daily_productios, label="production")
    pyplot.plot(x,daily_PDI_in, label="PDI-IN")
    pyplot.legend()
    pyplot.ylabel('Production')

    pyplot.subplot(3,1,2)
    pyplot.plot(x,daily_prePDI, label="Pre-PDI")
    pyplot.legend()
    pyplot.ylabel('Pre-PDI')
    pyplot.ylim(0, max(daily_prePDI))

    pyplot.subplot(3,1,3)
    pyplot.plot(x,dailiy_repairWaiting, label="repair")
    pyplot.plot(x,daily_partsWaiting, label="parts")
    pyplot.legend()
    pyplot.ylabel('Block Stock')
    st.pyplot(fig)


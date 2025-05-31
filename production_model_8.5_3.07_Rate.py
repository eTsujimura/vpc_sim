#-------------------------------------------------------------------------------
# Name:        VPC simulator
# Purpose:     Watch VPC car flows status every minutes
#
# Author:      U640919 (Ei Tsujimura)
#
# Created:     02/04/2024
# Copyright:   (c) U640919 2024
# Licence:     <your licence>
#-------------------------------------------------------------------------------


"""
2024 - 2025 : 40,000 / year --> ave. 167 / Day
2026 - 2027 : 5.,000 / year --> ave. 208 / Day
* 240 working day
"""

CURR_CLOCK = 0
NUMBER_OF_LINES = 1  # simulation is done for 1 line and dupilicate result for lines
PER_SHIFT_MAX_CLOCK = 8*60  # 8 hours
SHIFT_PER_DAY = 2
SIMULATE_DAYS = 80
TAKT_TIME = 8
REPAIR_BAYS = 18 # Per line,  70% of actual bays
DELTA = 1.00*SHIFT_PER_DAY
INITIAL_STOCK = 0
ETA = ([0] + [1000] + [0]*60)
ETA.reverse()  # get ready for .pop()
ANNUAL_IMPORT_CARS = int(sum(ETA) / NUMBER_OF_LINES + 100)
PARTS_REQURED = 30  # 30% 86/285
DEFECT_RATE = [[0, 3.07], [80, 3.07]]  # 10% no_repair, 80-10% 2 hours, 100-80%, 20.5 hours | [[10, 2], [80, 20.5]] | [[50, 2], [85, 10.5]]
PARTS_LEADTIME = [[0, 1], [80, 60]]  # 85% 1 Day, 15% 60 days | [[0, 1], [85, 60]] | [[0, 1], [85, 60]]
# [[X, A], [Y, B]]
# |     |       |       |       |
# 0     X               Y       100
# Flase |       A       |   B   |


import random
from matplotlib import pyplot

def return_true_x_percent(x):
    random_number = random.random()
    return random_number <= x/100


def return_repairtime_x_persent(dRate):
    """
    return false for x %
    return A for y -x %
    return B for 100 - y %
    DEFECT_RATE = [[0, 1.78], [80, 1.78]]
    """
    random_number = random.random()
    if random_number <= dRate[0][0]/100:
        return False

    elif random_number <= dRate[1][0]/100:
        return dRate[0][1]

    else:
        return dRate[1][1]



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
        #  print("[{0}]".format(self.name))
        #  print("Next Slot buffer from {}".format(self.nextSlot.buffer))
        self.nextSlot.buffer += 1
        #  print("Next Slot buffer to {}\n".format(self.nextSlot.buffer))
        return True


    def new(self):
        if self.active:
            self.comment = self.comment + "Not ready for next, "
            return False

        if self.buffer == 0:
            self.comment = self.comment + "No buffer, "
            return False

        # Start new one
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
        print("{0:<20}: | [Buffer] {1:>5} | [Active] {2:>3} | [complete]{3:>5} | [Cnt] {4:>3} | {5}".format(self.name, self.buffer, self.active, self.complete, self.cnt, self.comment))



class Slot_branch(Slot):
    """
    Send car(s) to designated slot depenfing on condition
    """
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
        ## self.comment = self.comment + "requred repair = {}, ".format(detection)

        if detection==False:
            # go to next std slot
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
        print("{0:<20}: | [inBuffer] {1:>5} | [parts waiting ]{2:>3} |Slots  {3} | {4} ".format(self.name, len(self.in_buffer), len(self.partsWaiting), self.bays, self.comment))



    def deliver(self):
        self.complete += 1
        if self.nextSlot.buffer >= self.nextSlot.maxBuffer:
            # Not working for now, instead unlimited buffer before final inspection
            self.comment = self.comment + "Sent to out_buffer, "
            return False

        else:
            self.comment = self.comment + "Delivered(STD), "
            self.nextSlot.buffer += 1
            return True


    def countUp(self):
        self.comment = ""  # reset comment

        # counting down labour time
        if len(self.bays) > 0:
            self.bays = [i-1 for i in self.bays]

        # Check how many completed
        complete = self.bays.count(0)
        if complete > 0:
            self.comment = self.comment + "{} completed, ".format(complete)
            for i in range(complete):
                self.deliver()

            # Removing completed from slots
            self.bays = [i for i in self.bays if i !=0]


        # bring from out buffer if available
        # print("Occupid bay={0} | MaxSlot={1} | waiting={2}".format(len(self.bays), self.repairSlots, len(self.in_buffer)))
        if len(self.bays) < self.repairSlots:
            try:
                pop = self.in_buffer.pop(0)
                # print("bring it up!")
                self.bays.append(pop)

            except:
                pass

        else:
            # print("Keep it as is")  # commentOut
            pass


    def nextDay(self):
        # counting down day
        self.partsWaiting = [[l[0], l[1]-1] for l in self.partsWaiting]

        # Move parts from parts waiting to repair waiting if day cnt = 0
        tmp_pw = self.partsWaiting  # copy parts waiting
        self.partsWaiting = []  # reset parts waiting
        for l in tmp_pw:
            if l[1] <= 0:
                self.in_buffer.append(l[0])
                #  print("Moved to repair waiting")

            else:
                self.partsWaiting.append(l)



class VPC():
    def __init__(self):
        self.time = 0
        ENTRY_CARS = int(ETA.pop()/NUMBER_OF_LINES)   # overwrite with ETA list

        self.s01 = Slot("Entry", maxBuffer=ANNUAL_IMPORT_CARS, buffer=ENTRY_CARS, takt=TAKT_TIME)
        self.s02 = Slot("Function check", takt=TAKT_TIME)
        self.s03 = Slot("Exterior check 1", takt=TAKT_TIME)
        self.s04 = Slot("Exterior check 2", takt=TAKT_TIME)
        self.s05 = Slot_branch("Interior check", takt=TAKT_TIME)
        self.r01 = RepairSlots("Generl repair", REPAIR_BAYS)
        self.s06 = Slot("Final check", maxBuffer=ANNUAL_IMPORT_CARS+200, takt=TAKT_TIME)
        self.p01 = Slot("Parking", maxBuffer=ANNUAL_IMPORT_CARS+200, buffer=0, takt=TAKT_TIME)


        # setting slots relation
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

        # commentOut_001
        """
        self.s01.status()
        self.s02.status()
        self.s03.status()
        self.s04.status()
        self.s05.status()
        self.r01.status()
        self.s06.status()
        self.p01.status()
        """

        self.s01.countUp()
        self.s02.countUp()
        self.s03.countUp()
        self.s04.countUp()
        self.s05.countUp()
        self.r01.countUp()
        self.s06.countUp()

        # commentOut_002
        """
        print("Global time : {0:0.2f}".format(self.time/60))
        print("==Waiting for repair==")
        print(self.r01.in_buffer)
        print("==Waiting for parts==")
        print(self.r01.partsWaiting)
        print("====================================")
        """


    def block_stock_status(self):
        report = "Produced from Day 1 = {} \n\n".format(self.p01.buffer*NUMBER_OF_LINES)
        report = report + "==Waiting for repair== | TTL = {} \n".format(len(self.r01.in_buffer)*NUMBER_OF_LINES)
        # report = report + str(self.r01.in_buffer*NUMBER_OF_LINES)  # commentOut
        report = report + "\n\n"
        report = report + "==Waiting for parts== | TTL = {} \n".format(len(self.r01.partsWaiting)*NUMBER_OF_LINES)
        # report = report + str(self.r01.partsWaiting*NUMBER_OF_LINES)  # commentOut
        blocked_cars = len(self.r01.in_buffer) + len(self.r01.partsWaiting)
        inprocess_cars = (self.s01.complete - self.p01.buffer - blocked_cars)*NUMBER_OF_LINES
        blocked_cars = blocked_cars * NUMBER_OF_LINES  # Mitiply after inprosess calculated
        report = report + "\n====== \nTTL Blocked = {0}  | TTL in-process = {1} \n".format(blocked_cars, inprocess_cars)
        report = report + "\n"
        return report



def main():
    v = VPC()
    lastReport = "\n ■■■■■■■ FINAL REPORT ■■■■■■■■ \n"

    # for counting production
    init_production = 0
    PDI_in_cnt = 0
    daily_PDI_in = []
    daily_productios = []
    dailiy_repairWaiting = []
    daily_partsWaiting = []
    daily_inprocess = []
    daily_prePDI = []
##    vessel_cnt = 0   # comment out

    for d in range(SIMULATE_DAYS):
        # print("==== ■ Day {} START====".format(d+1))  # commentOut
        for m in range(int(PER_SHIFT_MAX_CLOCK*SHIFT_PER_DAY)+1):
            v.tick()

        # Vessel ETA
        try:
            arrived_cars = int(ETA.pop()/NUMBER_OF_LINES)

        except:
            arrived_cars = 0


        print("car {}".format(v.s01.buffer))
        v.s01.buffer += arrived_cars
        print("Vessel ETA {}".format(arrived_cars))

        ## vessel_cnt +=1
        ## only for testing
        v.s01.status()
        v.s02.status()
        v.s03.status()
        v.s04.status()
        v.s05.status()
        v.r01.status()
        v.s06.status()
        v.p01.status()
        print("#################################\n")

        # print("==== ■ Day {} END ====".format(d+1))  # commentOut
        # lastReport = lastReport + "==== ■ Day {}  ====\n".format(d+1)  # commentOut

        # PDI in
        cnt = v.s01.complete - PDI_in_cnt  # last day count
        daily_PDI_in.append(cnt)
        PDI_in_cnt = v.s01.complete  # update to end of the day

        # adding production volume on top

        ttl_produced = v.p01.buffer
        daily_productios.append((ttl_produced - init_production) * NUMBER_OF_LINES)
        init_production = ttl_produced

        blocked_cars = len(v.r01.in_buffer) + len(v.r01.partsWaiting)
        #  daily_inprocess.append((v.s01.complete - v.p01.buffer - blocked_cars)*NUMBER_OF_LINES) #  include under repair
        daily_inprocess.append((v.s06.buffer)*NUMBER_OF_LINES)
        daily_prePDI.append((v.s01.buffer)*NUMBER_OF_LINES)
        dailiy_repairWaiting.append(len(v.r01.in_buffer)*NUMBER_OF_LINES)
        daily_partsWaiting.append(len(v.r01.partsWaiting)*NUMBER_OF_LINES)
        #  lastReport = lastReport + "Daily production = {0}\n".format(daily_productios)  # commentOut


        #  print(r)  # commentOut
        #  lastReport = lastReport + r + "\n"  # commentOut
        v.r01.nextDay()   # shift from parts waiting to repair waiting

    r = v.block_stock_status()
    lastReport = lastReport + "Daily production : \n{0}\n\n".format(daily_productios)
    lastReport = lastReport + "Daily repair waiting :\n{}\n\n".format(dailiy_repairWaiting)
    lastReport = lastReport + "Daily parts waiting :\n{}\n\n".format(daily_partsWaiting)
    lastReport = lastReport + r + "\n"
    print(lastReport)

    print("###### Slots sttus ######")
    v.s01.status()
    v.s02.status()
    v.s03.status()
    v.s04.status()
    v.s05.status()
    v.r01.status()
    v.s06.status()
    v.p01.status()

    print("###### max. parts waiting######")
    print(max(daily_partsWaiting))

    print("###### max. repair waiting ######")
    print(max(dailiy_repairWaiting))

    print("###### max. buffer before final ######")
    print(max(daily_inprocess))

    print("###### max. parking ######")
    z = zip(daily_partsWaiting, dailiy_repairWaiting, daily_inprocess)
    daily_combined = [x + y + z for (x, y, z) in z]
    print(max(daily_combined))
    ## print(list(daily_combined))


    # Draw graph

    x = range(SIMULATE_DAYS)
    fig = pyplot.figure(figsize=(8,5))
    # fig.suptitle('title')
    pyplot.subplot(3,1,1)
    pyplot.plot(x,daily_productios, label="production")
    pyplot.plot(x,daily_PDI_in, label="PDI-IN")
    pyplot.legend()
    pyplot.ylabel('Production')

    pyplot.subplot(3,1,2)
    pyplot.plot(x,daily_prePDI, label="Pre-PDI")
    pyplot.legend()
    pyplot.ylabel('Rre-PDI')
    pyplot.ylim(0, max(daily_prePDI))

    pyplot.subplot(3,1,3)
    pyplot.plot(x,dailiy_repairWaiting, label="repair")
    pyplot.plot(x,daily_partsWaiting, label="parts")
    pyplot.legend()
    pyplot.ylabel('Block Stock')
    pyplot.show()

    """
    production_plot = pyplot.plot
    production_plot(range(SIMULATE_DAYS), daily_partsWaiting)
    production_plot.show()
    """



if __name__ == '__main__':
    main()
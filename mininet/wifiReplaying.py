"""

author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
        ramonfontes.com

"""

import time
import threading
import random
from pylab import math, cos, sin
from mininet.log import info
from mininet.wifiPlot import plot
from mininet.wifiMobility import mobility
from mininet.wifiChannel import channelParameters
from mininet.wifiDevices import deviceDataRate


def instantiateGraph():
        nodeList = mobility.staList + mobility.apList
        for node in nodeList:
            plot.instantiateGraph(mobility.MAX_X, mobility.MAX_Y)
            plot.instantiateNode(node, mobility.MAX_X, mobility.MAX_Y)
            plot.instantiateAnnotate(node)
            plot.instantiateCircle(node)
            plot.graphUpdate(node)

class replayingMobility(object):
    """Replaying Mobility Traces"""
    def __init__(self, **params):

        mobility.isMobility = True
        self.thread = threading.Thread(name='replayingMobility', target=self.mobility)
        self.thread.daemon = True
        self.thread.start()

    def mobility(self):
        if mobility.DRAW:
            instantiateGraph()
        currentTime = time.time()
        staList = mobility.staList
        continue_ = True
        nodeTime = {}
        nodeCurrentTime = {}
        for node in staList:
            nodeCurrentTime[node] = 1 / node.params['speed']
            nodeTime[node] = float(1.0 / node.params['speed'])
        while continue_:
            continue_ = False
            time_ = time.time() - currentTime
            for node in staList:
                continue_ = True
                while time_ >= nodeCurrentTime[node] and len(node.position) != 0:
                    node.moveStationTo(node.position[0])
                    del node.position[0]
                    nodeCurrentTime[node] += nodeTime[node]
                if len(node.position) == 0:
                    staList.remove(node)
            time.sleep(0.01)

class replayingBandwidth(object):
    """Replaying Bandwidth Traces"""

    def __init__(self, **params):

        self.thread = threading.Thread(name='replayingBandwidth', target=self.throughput)
        self.thread.daemon = True
        self.thread.start()

    def throughput(self):
        # if mobility.DRAW:
        #    plotGraph()
        currentTime = time.time()
        staList = mobility.staList
        continue_ = True
        while continue_:
            continue_ = False
            time_ = time.time() - currentTime
            for sta in staList:
                if hasattr(sta, 'time'):
                    continue_ = True
                    if time_ >= sta.time[0]:
                        channelParameters.tc(sta, 0, sta.throughput[0], 0, 0, 0)
                        # pos = '%d, %d, %d' % (sta.throughput[0], sta.throughput[0], 0)
                        # self.moveStationTo(sta, pos)
                        del sta.throughput[0]
                        del sta.time[0]
                        info('%s\n' % sta.time[0])
                    if len(sta.time) == 1:
                        staList.remove(sta)
            # time.sleep(0.001)
        info("\nReplaying Process Finished!")

    def moveStationTo(self, sta, pos):
        x = pos[0]
        y = pos[1]
        sta.params['position'] = x, y, 0
        # mobility.getAPsInRange(sta)
        if mobility.DRAW:
            try:
                plot.graphUpdate(sta)
            except:
                pass

class replayingRSSI(object):
    """Replaying RSSI Traces"""

    def __init__(self, propagationModel='friisPropagationLossModel'):
        mobility.isMobility = True
        self.thread = threading.Thread(name='replayingRSSI', target=self.rssi, args=(propagationModel,))
        self.thread.daemon = True
        self.thread.start()

    def rssi(self, propagationModel=''):
        if mobility.DRAW:
            instantiateGraph()
        currentTime = time.time()
        staList = mobility.staList
        ang = {}
        for sta in staList:
            ang[sta] = random.uniform(0, 360)
            sta.params['frequency'][0] = channelParameters.frequency(sta, 0)
        continue_ = True
        while continue_:
            continue_ = False
            time_ = time.time() - currentTime
            for sta in staList:
                if hasattr(sta, 'time'):
                    continue_ = True
                    if time_ >= sta.time[0]:
                        ap = sta.params['associatedTo'][0]  # get AP
                        sta.params['rssi'][0] = sta.rssi[0]
                        if ap != '':
                            dist = self.calculateDistance(sta, ap, sta.rssi[0], propagationModel)
                            self.moveStationTo(sta, ap, dist, ang[sta])
                            loss = channelParameters.loss(dist)
                            latency = channelParameters.latency(dist)
                            delay = channelParameters.delay(dist, 0)
                            bw = channelParameters.bw(sta, ap, dist, 0, isReplay=True)
                            channelParameters.tc(sta, 0, bw, loss, latency, delay)
                        del sta.rssi[0]
                        del sta.time[0]
                    if len(sta.time) == 0:
                        staList.remove(sta)
            time.sleep(0.01)

    def moveStationTo(self, sta, ap, dist, ang):
        x = dist * cos(ang) + int(ap.params['position'][0])
        y = dist * sin(ang) + int(ap.params['position'][1])
        sta.params['position'] = x, y, 0
        mobility.getAPsInRange(sta)
        if mobility.DRAW:
            try:
                plot.graphUpdate(sta)
            except:
                pass
        # sta.verifyingNodes(sta)

    def calculateRate(self, sta, ap, dist):
        value = deviceDataRate(sta, ap, 0)
        custombw = value.rate
        rate = value.rate / 2.5
        if ap.equipmentModel == None:
            rate = custombw * (1.1 ** -dist)
        if rate <= 0:
            rate = 1
        return rate

    def calculateDistance (self, sta, ap, signalLevel, model=None):

        pT = ap.params['txpower'][0]
        gT = ap.params['antennaGain'][0]
        gR = sta.params['antennaGain'][0]

        if model in dir(self):
            dist = self.__getattribute__(model)(sta, ap, pT, gT, gR, signalLevel)
            return dist

    def pathLoss(self, sta, ap, dist, wlan=0):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        f = sta.params['frequency'][wlan] * 10 ** 9  # Convert Ghz to Hz
        c = 299792458.0
        L = 1
        if dist == 0:
            dist = 0.1
        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        numerator = (4 * math.pi * dist) ** 2 * L
        pathLoss_ = 10 * math.log10(numerator / denominator)

        return pathLoss_

    def friisPropagationLossModel(self, sta, ap, pT, gT, gR, signalLevel):
        """Based on Free Space Propagation Model"""
        c = 299792458.0
        L = 2.0
        freq = sta.params['frequency'][0] * 10 ** 9  # Convert Ghz to Hz
        gains = gR + gT + pT
        lambda_ = float(c) / float(freq)  # lambda: wavelength (m)
        numerator = 10.0 ** (abs(signalLevel - gains) / 10.0)
        dist = (lambda_ / (4.0 * math.pi)) * ((numerator / L) ** (0.5))

        return dist

    def logDistancePropagationLossModel(self, sta, ap, pT, gT, gR, signalLevel):
        """Based on Log Distance Propagation Loss Model"""
        gains = gR + gT + pT
        referenceDistance = 1
        exp = 2
        pathLossDb = self.pathLoss(sta, ap, referenceDistance)
        rssi = gains - signalLevel - pathLossDb
        dist = 10 ** ((rssi + 10 * exp * math.log10(referenceDistance)) / (10 * exp))

        return dist

    def ITUPropagationLossModel(self, sta, ap, pT, gT, gR, signalLevel):
        """Based on International Telecommunication Union (ITU) Propagation Loss Model"""
        N = 32.0  # Power Loss Coefficient
        lF = 0  # Floor penetration loss factor
        nFloors = 0  # Number of Floors
        gains = pT + gT + gR
        freq = sta.params['frequency'][0] * 10 ** 3
        dist = 10.0 ** ((-20.0 * math.log10(freq) - lF * nFloors + 28.0 + abs(signalLevel - gains)) / N)

        return dist

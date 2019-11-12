#!/usr/bin/env python3

import csv
import os
import json
import datetime
import re
import abc
import matplotlib.pyplot as pplot


def average(lst: list) -> float:
    return sum(lst) / len(lst)


class CsvAnalyzer(abc.ABC):
    def __init__(self):
        self.responsespersec = []
        self.latencypersec = []

    def getfiles(self, directory='.'):
        return[(directory + '/' + f) for f in os.listdir(directory) if f.endswith('.csvfile')]

    def walkresponsepersec(self, responsepersec, shouldprint):
        for sec in responsepersec:
            if len(responsepersec[sec]) != 0:
                self.responsespersec.append(len(responsepersec[sec]))
                self.latencypersec.append(average(responsepersec[sec]))
                if shouldprint:
                    print(len(responsepersec[sec]))
                    print(average(responsepersec[sec]))


class HeyAnalyzer(CsvAnalyzer):
    def processfile(
            self,
            fname,
            shouldprint: bool = False):
        with open(fname, 'r') as f:
            data = csv.reader(f)
            fields = next(data)
            responsepersec = {}
            for row in data:
                items = zip(fields, row)
                item = {}
                for(name, value) in items:
                    item[name] = value.strip()
                sec = int(item['offset'].split('.')[0])
                if sec not in responsepersec:
                    responsepersec[sec] = []
                else:
                    responsepersec[sec].append(float(item['response-time']))
            super().walkresponsepersec(responsepersec, shouldprint)

    def keychars(self, x):
        return int(x.split('.')[1])

    def processallfiles(self, directory='.'):
        files = sorted(super().getfiles(directory), key=self.keychars)
        for f in files:
            self.processfile(f, False)


class LogAnalyzer:
    def __init__(self):
        self.concurrencypersec = []
        self.podpersec = []
        self.start = datetime.datetime.now()
        self.end = datetime.datetime.now()

    def listtodict(self, inlist: list) -> dict:
        it = iter(inlist)
        res_dct = dict(zip(it, it))
        return res_dct

    def readfile(self, directory='.') -> dict:
        dictofsecs = {}
        with open(directory + "/log.txt", 'r') as inputFile:
            line = inputFile.readline()
            while line:
                try:
                    linedict = json.loads(line)
                    try:
                        currdate = linedict['ts'].split(
                            '.')[0].replace('T', ' ')
                        dateformatted = datetime.datetime.strptime(
                            currdate, '%Y-%m-%d %H:%M:%S')
                        if self.start < dateformatted < self.end:
                            message = linedict['msg']
                            messagelist = re.split('[ =]', message)
                            messagedict = self.listtodict(messagelist)
                            messagedict['ts'] = dateformatted
                            if 'ObservedStableValue' in messagedict:
                                if messagedict['ts'] not in dictofsecs:
                                    dictofsecs[messagedict['ts']] = {
                                        'pod': [], 'cc': []}
                                dictofsecs[messagedict['ts']]['pod'].append(
                                    float(messagedict['PodCount']))
                                dictofsecs[messagedict['ts']]['cc'].append(
                                    float(messagedict['ObservedStableValue']))
                    except Exception as exception:
                        print(exception)
                except json.JSONDecodeError:
                    continue
                finally:
                    line = inputFile.readline()
        return dictofsecs

    def readconfigdates(self, directory='.'):
        dates = []
        with open(directory + "/dates.txt", 'r') as inputFile:
            line = inputFile.readline().rstrip()
            currline = 0
            while line:
                dateformatted = datetime.datetime.strptime(
                    line, '%Y-%m-%d %H:%M:%S')
                dates.append(dateformatted)
                line = inputFile.readline().rstrip()
                currline += 1
        self.start = dates[0]
        self.end = dates[1]

    def averagepersec(
            self,
            dictoftimes: dict,
            shouldprint: bool = False) -> None:
        for key, value in dictoftimes.items():
            pod = value['pod']
            concurrency = value['cc']
            avgpod = average(pod)
            avgcc = average(concurrency)
            self.podpersec.append(avgpod)
            self.concurrencypersec.append(avgcc)
            if shouldprint:
                print(avgpod)
                print(avgcc)

    def work(self, directory: str = '.') -> None:
        self.readconfigdates(directory)
        filelines = self.readfile(directory)
        self.averagepersec(filelines, False)


class JmeterAnalyzer(CsvAnalyzer):
    def processfile(
            self,
            fname,
            shouldprint: bool = False):
        with open(fname, 'r') as f:
            data = csv.reader(f)
            fields = next(data)
            responsepersec = {}
            for row in data:
                items = zip(fields, row)
                item = {}
                for (name, value) in items:
                    item[name] = value.strip()
                sec = datetime.datetime.fromtimestamp(
                    int(item['timeStamp']) / 1000.0).strftime('%c')
                if sec not in responsepersec:
                    responsepersec[sec] = []
                responsepersec[sec].append(float(item['Latency']))

            super().walkresponsepersec(responsepersec, shouldprint)

    def processallfiles(self, directory='.'):
        files = super().getfiles(directory)
        for f in files:
            self.processfile(f, False)


class ChartCreator:
    def savecsvplot(self, csvfile: CsvAnalyzer, directory) -> None:
        print("Charting " + directory)
        pplot.plot(csvfile.responsespersec)
        pplot.title(directory)
        pplot.xlabel("Time (seconds)")
        pplot.ylabel("Response/sec")
        pplot.savefig(directory + "-rps.png")
        pplot.clf()
        pplot.plot(csvfile.latencypersec)
        pplot.title(directory)
        pplot.xlabel("Time (seconds)")
        pplot.ylabel("Response time (milliseconds)")
        pplot.savefig(directory + "-latency.png")
        pplot.clf()

    def doallruns(self):
        dirs = next(os.walk('.'))[1]
        for directory in dirs:
            abs_directory = os.path.abspath(directory)
            print(abs_directory)
            if 'JMETER' not in abs_directory.upper():
                hey = HeyAnalyzer()
                hey.processallfiles(abs_directory)
                self.savecsvplot(hey, directory)
            else:
                jmeter = JmeterAnalyzer()
                jmeter.processallfiles(abs_directory)
                self.savecsvplot(jmeter, directory)
            try:
                log = LogAnalyzer()
                log.work(abs_directory)
                print("Charting " + directory + " Knative logs")
                pplot.plot(log.concurrencypersec)
                pplot.title(directory)
                pplot.xlabel("Time (seconds)")
                pplot.ylabel("ObsevedStableConcurrency")
                pplot.savefig(directory + "-cc.png")
                pplot.clf()
                pplot.plot(log.podpersec)
                pplot.title(directory)
                pplot.xlabel("Time (seconds)")
                pplot.ylabel("Pod count")
                pplot.savefig(directory + "-pod.png")
                pplot.clf()
            except Exception as e:
                print(e)


if __name__ == "__main__":
    cc = ChartCreator()
    cc.doallruns()

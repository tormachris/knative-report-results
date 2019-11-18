#!/usr/bin/env python3

"""
Python module to automatically analyze bechmark results
"""


import csv
import os
import json
import datetime
import re
import abc
import multiprocessing
import matplotlib.pyplot as pplot


def average(lst: list) -> float:
    """
    Agerage of list
    :param lst:
    :return:
    """
    return sum(lst) / len(lst)


def keychars(x):
    """
    Return hey partnumber
    :param x:
    :return:
    """
    return int(x.split('.')[1])


class Analyzer(abc.ABC):
    """
    Very abstract analyzer
    """

    def __init__(self, typeof='.csv'):
        self.type = typeof

    def getfiles(self, directory: str = '.') -> list:
        """
        Returns a list of csv files in directory
        :param directory:
        :return:
        """
        return[(directory + '/' + filename) for filename in os.listdir(directory) if filename.endswith(self.type)]

    def processfile(
            self,
            fname,
            shouldprint: bool = False):
        pass

    def processallfiles(self, directory='.'):
        """
        Process all files in a directory
        :param directory:
        :return:
        """
        files = sorted(self.getfiles(directory), key=keychars)
        for f in files:
            self.processfile(f, False)


class CsvAnalyzer(Analyzer):
    """
    Abstract CSV analyzer
    """

    def __init__(self):
        """
        Init object
        """
        super().__init__()
        self.responsespersec = []
        self.latencypersec = []

    def walkresponsepersec(
            self,
            responsepersec: dict,
            shouldprint: bool) -> None:
        """
        Walks through reponsepersec dict
        :param responsepersec:
        :param shouldprint:
        :return:
        """
        for sec in responsepersec:
            if len(responsepersec[sec]) != 0:
                self.responsespersec.append(len(responsepersec[sec]))
                self.latencypersec.append(average(responsepersec[sec]))
                if shouldprint:
                    print(len(responsepersec[sec]))
                    print(average(responsepersec[sec]))


class HeyAnalyzer(CsvAnalyzer):
    """
    Analyze hey benchmark output.
    """

    def __init__(self):
        """
        Init object
        """
        super().__init__()

    def processfile(
            self,
            fname,
            shouldprint: bool = False):
        """
        Process a single file.
        :param fname:
        :param shouldprint:
        :return:
        """
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
            self.walkresponsepersec(responsepersec, shouldprint)


class LogAnalyzer(Analyzer):
    """
    Analyze Knative logs
    """

    def __init__(self):
        """
        Init object
        """
        super().__init__(typeof='.txt')
        self.concurrencypersec = []
        self.podpersec = []
        self.start = datetime.datetime.now()
        self.end = datetime.datetime.now()

    def listtodict(self, inlist: list) -> dict:
        """
        Turns a list into a dict
        :param inlist:
        :return:
        """
        it = iter(inlist)
        res_dct = dict(zip(it, it))
        return res_dct

    def processfile(
            self,
            fname,
            shouldprint: bool = False) -> dict:
        """
        Read logfile
        :param fname:
        :param shouldprint:
        :return:
        """
        dictofsecs = {}
        if 'date' in fname:
            return {}
        with open(fname, 'r') as inputFile:
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
        """
        Read dates.txt and configure object
        :param directory:
        :return:
        """
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
        """
        Average lists
        :param dictoftimes:
        :param shouldprint:
        :return:
        """
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
        """
        Main interface
        :param directory:
        :return:
        """
        files = super().getfiles(directory)
        self.readconfigdates(directory)
        filelines = {}
        for afile in files:
            filelines.update(self.processfile(afile))
        self.averagepersec(filelines, False)


class JmeterAnalyzer(CsvAnalyzer):
    """
    Jmeter benchmark tool analyzer
    """

    def __init__(self):
        """
        Init object
        """
        super().__init__()
        self.responsepersec = {}

    def processfile(
            self,
            fname,
            shouldprint: bool = False):
        """
        Process benchmark result file.
        :param fname:
        :param shouldprint:
        :return:
        """
        with open(fname, 'r') as f:
            data = csv.reader(f)
            fields = next(data)
            for row in data:
                items = zip(fields, row)
                item = {}
                for (name, value) in items:
                    item[name] = value.strip()
                sec = datetime.datetime.fromtimestamp(
                    int(item['timeStamp']) / 1000.0).strftime('%c')
                if sec not in self.responsepersec:
                    self.responsepersec[sec] = []
                self.responsepersec[sec].append(float(item['Latency']))

    def collectinfo(self, shouldprint: bool = False) -> None:
        """
        Collect info
        :param shouldprint:
        :return:
        """
        self.walkresponsepersec(self.responsepersec, shouldprint)


class ChartCreator:
    """
    Create charts automagically
    """

    @staticmethod
    def savetxtplot(csvfile: CsvAnalyzer, directory) -> None:
        """
        Save raw data to txt
        :param directory:
        :param csvfile:
        :return:
        """
        with open(os.getenv('TEXTDIR', default='.') + '/' + directory + "-rps.txt", 'w') as f:
            for item in csvfile.responsespersec:
                f.write("%s\n" % item)
        with open(os.getenv('TEXTDIR', default='.') + '/' + directory + "-latency.txt", 'w') as f:
            for item in csvfile.latencypersec:
                f.write("%s\n" % item)


    @staticmethod
    def savecsvplot(csvfile: CsvAnalyzer, directory) -> None:
        """
        Save plot of csv file
        :param csvfile:
        :param directory:
        :return:
        """
        pplot.plot(csvfile.responsespersec)
        pplot.title(directory)
        pplot.xlabel("Time (seconds)")
        pplot.ylabel("Response/sec")
        pplot.savefig(os.getenv('CHARTDIR', default='.') + '/' + directory + "-rps.png")
        pplot.clf()
        pplot.plot(csvfile.latencypersec)
        pplot.title(directory)
        pplot.xlabel("Time (seconds)")
        pplot.ylabel("Response time (milliseconds)")
        pplot.savefig(os.getenv('CHARTDIR', default='.') + '/' + directory + "-latency.png")
        pplot.clf()
        print("Charted " + directory)

    @staticmethod
    def analyze_jmeter(abs_directory, directory):
        """
        Analyze Jmeter output
        :param abs_directory:
        :param directory:
        :return:
        """
        jmeter = JmeterAnalyzer()
        jmeter.processallfiles(abs_directory)
        jmeter.collectinfo(False)
        ChartCreator.savecsvplot(jmeter, directory)
        ChartCreator.savetxtplot(jmeter,directory)

    @staticmethod
    def analyze_hey(abs_directory, directory):
        """
        Analyze hey output
        :param abs_directory:
        :param directory:
        :return:
        """
        hey = HeyAnalyzer()
        hey.processallfiles(abs_directory)
        ChartCreator.savecsvplot(hey, directory)
        ChartCreator.savetxtplot(hey, directory)

    @staticmethod
    def analyze_logs(abs_directory, directory):
        """
        Analyze knative logs
        :param abs_directory:
        :param directory:
        :return:
        """
        try:
            log = LogAnalyzer()
            log.work(abs_directory)
            print("Charting " + directory + " Knative logs")
            pplot.plot(log.concurrencypersec)
            pplot.title(directory)
            pplot.xlabel("Time (seconds)")
            pplot.ylabel("ObsevedStableConcurrency")
            pplot.savefig(os.getenv('CHARTDIR', default='.') + '/' + directory + "-cc.png")
            pplot.clf()
            pplot.plot(log.podpersec)
            pplot.title(directory)
            pplot.xlabel("Time (seconds)")
            pplot.ylabel("Pod count")
            pplot.savefig(os.getenv('CHARTDIR', default='.') + '/' + directory + "-pod.png")
            pplot.clf()
            with open(os.getenv('TEXTDIR', default='.') + '/' + directory + "-pods.txt", 'w') as f:
                for item in log.podpersec:
                    f.write("%s\n" % item)
            with open(os.getenv('TEXTDIR', default='.') + '/' + directory + "-cc.txt", 'w') as f:
                for item in log.concurrencypersec:
                    f.write("%s\n" % item)
        except Exception as exception:
            print(exception)

    def doallruns(self):
        """
        Process all directories in repo
        :return:
        """
        dirs = next(os.walk(os.getenv('SEARCHDIR', default='.')))[1]
        jobs = []
        for directory in dirs:
            abs_directory = os.getenv(
                'SEARCHDIR', default='.') + '/' + directory
            print(abs_directory)
            if 'JMETER' not in abs_directory.upper():
                process = multiprocessing.Process(target=ChartCreator.analyze_hey, args=(abs_directory, directory,))
            else:
                process = multiprocessing.Process(target=ChartCreator.analyze_jmeter, args=(abs_directory, directory,))

            jobs.append(process)
            process.start()
            logprocess = multiprocessing.Process(target=ChartCreator.analyze_logs, args=(abs_directory, directory,))
            jobs.append(logprocess)
            logprocess.start()


if __name__ == "__main__":
    """
    Entry point
    """
    chartcreator = ChartCreator()
    chartcreator.doallruns()

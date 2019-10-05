import os
import time
import requests
import json
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily, REGISTRY

class StorjCollector(object):
  def __init__(self):
    self.storj_host_address = os.environ.get('STORJ_HOST_ADDRESS', '127.0.0.1')
    self.storj_api_port = os.environ.get('STORJ_API_PORT', '14002')

  def call_api(self,path):
    response=requests.get(url = "http://" + self.storj_host_address + ":" + self.storj_api_port + "/api/" + path)
    return response.json()
   
  def get_data(self):
    return self.call_api("dashboard")['data']

  def get_satellites(self):
    satellites = []
    for item in self.data['satellites']:
      satellites.append(item['id'])
    return satellites

  def get_sat_data(self):
    array = {}
    for sat in self.satellites:
      data = self.call_api("satellite/" + sat)['data']
      array.update({sat : data})
    return array  

  def collect(self):
    self.data = self.get_data()
    self.satellites = self.get_satellites()
    self.sat_data = self.get_sat_data()
    for key in ['nodeID','wallet','lastPinged','lastPingFromID','lastPingFromAddress','upToDate']:
      value = str(self.data[key])
      metric = InfoMetricFamily("storj_" + key, "Storj " + key, value={key : value})
      yield metric

    for array in ['diskSpace','bandwidth']:
      for key in ['used','available']:
        value = self.data[array][key]
        metric = GaugeMetricFamily("storj_" + array + "_" + key, "Storj " + array + " " + key, value=value)
        yield metric

    for array in ['audit','uptime']:
      for key in list(self.sat_data.values())[0][array]:
        metric = GaugeMetricFamily("storj_sat_" + array + "_" + key, "Storj satellite " + key,labels=["satellite"])
        for sat in self.satellites:
          value = self.sat_data[sat][array][key]
          metric.add_metric([sat], value)
        yield metric
    
    for key in ['storageSummary','bandwidthSummary']:
      metric = GaugeMetricFamily("storj_sat_" + key, "Storj satellite " + key,labels=["satellite"])
      for sat in self.satellites:
        value = self.sat_data[sat][key]
        metric.add_metric([sat], value)
      yield metric

    metric = GaugeMetricFamily("storj_sat_month_egress", "Storj satellite egress since current month start", labels=["satellite","type"],)
    for key in ['repair','audit','usage']:
      for sat in self.satellites:
        value=0
        for day in list(self.sat_data[sat]['bandwidthDaily']):
          value=value + day['egress'][key]
        metric.add_metric([sat, key], value)
    yield metric
    
    metric = GaugeMetricFamily("storj_sat_month_ingress", "Storj satellite ingress since current month start", labels=["satellite","type"],)
    for key in ['repair','usage']:
      for sat in self.satellites:
        value=0
        for day in list(self.sat_data[sat]['bandwidthDaily']):
          value=value + day['ingress'][key]
        metric.add_metric([sat, key], value)
    yield metric

    metric = GaugeMetricFamily("storj_sat_day_egress", "Storj satellite egress since current day start", labels=["satellite","type"],)
    for key in ['repair','audit','usage']:
      for sat in self.satellites:
        value=self.sat_data[sat]['bandwidthDaily'][-1]['egress'][key]
        metric.add_metric([sat, key], value)
    yield metric

    metric = GaugeMetricFamily("storj_sat_day_ingress", "Storj satellite ingress since current day start", labels=["satellite","type"],)
    for key in ['repair','usage']:
      for sat in self.satellites:
        value=self.sat_data[sat]['bandwidthDaily'][-1]['ingress'][key]
        metric.add_metric([sat, key], value)
    yield metric


    metric = GaugeMetricFamily("storj_sat_month_storage", "Storj satellite data stored on disk since current month start", labels=["satellite"],)
    for sat in self.satellites:
      value=0
      for day in list(self.sat_data[sat]['storageDaily']):
        value=value + day['atRestTotal']
      metric.add_metric([sat], value)
    yield metric

    metric = GaugeMetricFamily("storj_sat_day_storage", "Storj satellite data stored on disk since current day start", labels=["satellite"],)
    for sat in self.satellites:
      value=self.sat_data[sat]['storageDaily'][-1]['atRestTotal']
      metric.add_metric([sat], value)
    yield metric

if __name__ == "__main__":
  storj_exporter_port = os.environ.get('STORJ_EXPORTER_PORT', '9651')
  REGISTRY.register(StorjCollector())
  start_http_server(int(storj_exporter_port))
  while True: time.sleep(1)

#!/usr/bin/env python

import BaseHTTPServer, urlparse, serial, ConfigParser, re, time, shutil, sys

config = ConfigParser.ConfigParser()
config.read((
    'lighted.conf',
    sys.path[0] + '/lighted.conf',
    '/etc/lighted.conf'
))

serialPort = config.get('lighted', 'serialport')
port = serial.Serial(serialPort, 115200, timeout=1)

devices = config.get('lighted', 'dmxdevices')
offsets = devices.split(',')

dmxDevices = {}
offset = 0
for device in offsets:
    offset += 1
    dmxDevices[offset] = int(device)

# Default to everything off
devices_old = dmxDevices.keys()
rgb_old = ['0','0','0']

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Disable logging DNS lookups
    def address_string(self):
        return str(self.client_address[0])

    def do_GET(self):
        url = urlparse.urlparse(self.path)
        params = urlparse.parse_qs(url.query)
        path = url.path

        if path == '/':
            path = '/resources/index.html'
        elif path == '/favicon.ico':
            path = '/resources/favicon.ico'

        bits = path.lstrip('/').split('/')

        # Serve the control page resources
        if bits[0] == 'resources':

            try:
                f = open('%s/%s/%s' % (sys.path[0], bits[0], bits[1]), 'rb')
            except IOError, e:
                self.send_error(404, "File not found")
                return
            
            self.send_response(200)
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
            f.close()
            return

        # Process a light change control request
        if len(bits) != 2:
            self.send_error(500)
            self.end_headers()
            self.wfile.write('Bad request, should be in the format foo.com/device/r,g,b')
            return 


        device = bits.pop(0) # Device
        if (device == '_'):
            devices = dmxDevices.keys()
        else:
            try:
                devices = device.split(',')
                devices = [int(x) for x in devices]

                for dev in devices:
                    if dev not in dmxDevices:
                        raise ValueError('Cannot find specified DMX device, available devices are: ')

            except ValueError, e:
                self.send_error(500)
                self.end_headers()
                self.wfile.write(e)
                self.wfile.write(', '.join(str(x) for x in dmxDevices.keys()))
                return 

        colour = bits.pop(0) # Colour
        try:
          if re.match('\d+,\d+,\d+', colour):
              rgb = colour.split(',')
          elif re.match('[0-9ABCDEF]{,6}', colour):
              rgb = [int(x, 16) for x in (colour[0:2], colour[2:4], colour[4:6])]

          for val in rgb:
              if int(val) < 0 or int(val) > 255:
                  raise ValueError('RGB value out of range, should be 0 <> 255')

        except ValueError, e:
            self.send_error(500)
            self.end_headers()
            self.wfile.write(e)
            return 

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('OK')
        self.setColour(devices, rgb)

        global devices_old, rgb_old
        if 'restoreAfter' in params:
            time.sleep(float(params['restoreAfter'][0]))
            self.setColour(devices_old, rgb_old)
        else:
            devices_old = devices
            rgb_old = rgb

        
    def setColour(self, devices, rgb):
        for device in devices:
            for i in range(0, 3):
                port.write("%sc%sw" % (dmxDevices[device] + i, rgb[i]))
        

PORT = config.getint('lighted', 'tcpport')
httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)
httpd.serve_forever()

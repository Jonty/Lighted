import BaseHTTPServer, urlparse, serial, ConfigParser, re, time, shutil

config = ConfigParser.ConfigParser()
config.read(('lighted.conf', '/etc/lighted.conf'))

serialPort = config.get('lighted', 'serialport')
port = serial.Serial(serialPort, 115200, timeout=1)

devices = config.get('lighted', 'dmxdevices')
offsets = devices.split(',')

devices_old = []
rgb_old = []

dmxDevices = {}
offset = 0
for device in offsets:
    offset += 1
    dmxDevices[offset] = int(device)


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Disable logging DNS lookups
    def address_string(self):
        return str(self.client_address[0])

    def do_GET(self):
        url = urlparse.urlparse(self.path)
        params = urlparse.parse_qs(url.query)
        path = url.path

        bits = path.split('/')
        bits.pop(0) # Crap

        # Serve the root control page
        if len(bits) == 1 and bits[0] == '':
            bits = ['resources', 'index.html']

        # Serve the control page resources
        if len(bits) and bits[0] == 'resources':
            try:
                f = open('/'.join(bits), 'rb')
            except IOError:
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
            self.send_header('Content-Type', 'text/html')
            self.wfile.write('Bad request, should be in the format foo.com/device/r,g,b')
            return 

        devices = []
        device = bits.pop(0) # Device
        if (device == '_'):
            devices = dmxDevices.keys()
        else:
            devices = device.split(',')
            devices = [int(x) for x in devices]

        for dev in devices:
            if dev not in dmxDevices:
                self.send_error(500)
                self.end_headers()
                self.send_header('Content-Type', 'text/html')
                self.wfile.write('Cannot find specified DMX device, available devices are: ')
                self.wfile.write(', '.join(str(x) for x in dmxDevices.keys()))
                return 

        colour = bits.pop(0) # Colour
        if re.match('\d+,\d+,\d+', colour):
            rgb = colour.split(',')
        elif re.match('[0-9ABCDEF]{,6}', colour):
            rgb = [int(x, 16) for x in (colour[0:2], colour[2:4], colour[4:6])]

        for val in rgb:
            if int(val) < 0 or int(val) > 255:
                self.send_error(500)
                self.end_headers()
                self.send_header('Content-Type', 'text/html')
                self.wfile.write('RGB value out of range, should be 0 <> 255')
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
        

PORT = 8000
httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)
httpd.serve_forever()

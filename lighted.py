import BaseHTTPServer, urlparse, serial, ConfigParser

config = ConfigParser.ConfigParser()
config.read(('lighted.conf', '/etc/lighted.conf'))

serialPort = config.get('lighted', 'serialport')
port = serial.Serial(serialPort, 115200, timeout=1)

devices = config.get('lighted', 'dmxdevices')
offsets = devices.split(',')

dmxDevices = {}
offset = 0
for device in offsets:
    offset += 1
    dmxDevices[offset] = int(device)

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):

    url = urlparse.urlparse(self.path)
    path = url.path

    bits = path.split('/')
    bits.pop(0) # Crap

    if len(bits) != 4:
        self.send_error(500)
        self.end_headers()
        self.send_header('Content-Type', 'text/html')
        self.wfile.write('Bad request, should be in the format foo.com/device/r/g/b')
        return 

    devices = []
    device = bits.pop(0)
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

    for val in bits:
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

    for device in devices:
        for i in range(0, 3):
            port.write("%sc%sw" % (dmxDevices[device] + i, bits[i]))

PORT = 8000
httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)
httpd.serve_forever()

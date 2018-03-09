from euxfel_karabo_bridge import Client

krb_client = Client("tcp://localhost:4545")

for i in range(10):
    data = krb_client.next()
    det_data = data['SPB_DET_AGIPD1M-1/DET/detector']
    print("Client : received train ID {}".format(det_data['header.trainId']))
    print("Client : - detector image shape is {}, {} Mbytes".format(
        det_data['image.data'].shape, det_data['image.data'].nbytes/1024**2))

print("Client : Client stops reading here")

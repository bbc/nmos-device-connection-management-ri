# NMOS Connection Management API Reference Implementation

## Introduction
This repository contains the reference implementation of the [NMOS Connection Management specification](https://github.com/AMWA-TV/nmos-device-connection-management), and other dependencies required to run it. It also contains a Vagrant file and provisioning script, which allows the API to be run in a virtual machine.

The VM will also present a user interface for interacting with the API, and another which allows senders and receivers to be added to a "mock driver". This mock driver takes the place of the interface that would normally exist between the API and a sender or receiver, and allows the user to add mock up senders or receivers to the connection management API. Note that the VM does not contain any actual RTP senders or receivers - you cannot produce media streams using this software.

## Setup

### Prerequisites

For the best experience:
- Use a host machine running Ubuntu Linux (tested on 16.04 and 14.04).
- Install vagrant using a Virtualbox as a provider (https://www.vagrantup.com/docs/installation/) (https://www.vagrantup.com/docs/virtualbox/).

The VM will bind to three host machine ports: 8080 to present the API itself, 8858 to present the mock driver user interfaces and 8860 to present the API user interface. If these ports are already in use on the host machine the bindings may be changed in the Vagrant file.

### Installing behind a proxy

[Optionally] Install vagrant proxyconf plugin if you want to easily pass host machine proxy configuration to the guest machines:
```
vagrant plugin install vagrant-proxyconf
```

Set environment http proxy variables (these will be passed to Vagrant VMs for use by git, apt and pip if Vagrant proxyconf plugin is installed):
```
export http_proxy=http://<path-to-your-proxy:proxy-port>
export https_proxy=https://<path-to-your-proxy:proxy-port>
```

For Windows users the proxy settings will have to be added to the vagrant file. Please see the [vagrant-proxyconf github](https://github.com/tmatilai/vagrant-proxyconf) for details.

### Start

To bring up the vagrant machine:

```
vagrant up
```

## Mock Driver User Interface

The mock driver is presented on (http://localhost:8858/). Two forms allow the creation of mock-up senders and receivers, which have the following options:

* Number of legs - Typically one unless SMPTE 2022-7 is use to allow use of a redundant path.
* Enable FEC - If checked the sender/receiver will expose parameters related to operation with forward error correction.
* Enable RTCP - If checked sender/receiver will expose parameters related to operation with RTCP.

Once added the sender or receiver's UUID will be listed in the table below the form, along with the settings used to create it. Clicking on the dustbin symbol on the right of each entry will remove the corresponding sender/receiver.

## API User Interface

The API user interface is presented on (http://localhost:8860/).

The interface defaults to expecting the API to be presented on http://localhost:8080. If this is not the case enter the root URL for the API (e.g http://localhost:12345) into the text box in the top left corner of the page, then click "Change API Root". If your browser supports HTML5, this value is saved to your browser, and will be remembered even if the page is refreshed.

If the API currently has senders and receivers registered their UUIDs will be listed below the "Senders" and "Receivers" headings. If no UUIDs are visible this may indicate that the root address for the API is set incorrectly. If using the example API presented by the VM ensure you have used the Mock Driver Interface (see above) to add some senders and receivers. Note that the page must be refreshed before new to update this list.

Clicking on the UUIDs causes a set of headings to appear beneath it. These are subtly different for senders and receivers. Click on a heading to expand its corresponding form. Each of the sections (for both senders and receivers) are detailed below:

### Staged Transport Parameters

Lists the staged transport parameters currently presented by the API. Only fields that are permitted by the sender/receiver's schema will be present. The "leg" drop down allows the user to toggle between parameters for the primary and redundant leg of SMPTE 2022-7 devices. Parameters for both legs must be populated before staging on such devices.

Clicking "Stage Parameters" makes an HTTP PUT request to the API. At present only PUT is supported by the UI, and as such all parameters will be updated to reflect their values in the form.


### Staged Transport File (Receivers Only)

This allows the transport file for a given receivers to be staged. "Transport File Type" should be set to application/sdp if working with SDP files. If passing in the actual content of the sdp file directly "By Reference" should be left un-checked. If passing in a URL to the transport file "By Reference" should be checked. The sdp file contents or the URL pointing to it should be placed in the "Data" box. Optionally the user may provide a Sender ID.

Clicking "Stage File" will staged these setting to the API. Once again only PUT is supported by the UI, however leaving "Sender ID" empty is acceptable, and will result in the Sender Id being set to "null".

### Activation

The activation form has a button for each of the activation types supported by the API - immediate, absolute and relative. Clicking "Activate Now" will transfer all staged parameters to active immediately. Clicking "Activate Relative" will move staged parameters to active after the offset defined by the "seconds" and "nanoseconds" fields has elapsed. Finally "Activate Absolute" will move the parameters at the TAI time provided in its own "seconds" and "nanoseconds" boxes. Note that TAI time differs from UTC, as it does not account for leap seconds.

During the period between a activation being requested and it occurring staged parameters are deemed to be "locked". Attempting to change the parameters during this time will result in an error.

### Active Transport File (Senders Only)

Provides a link to the transport file that should be used to configure receivers to receiver from this sender.

### Active Transport Parameters

Displays the transport parameters currently active on the device. The refresh button may be used to update these as required.

## Architecture

The reference implementation is written in Python, and is designed to be as modular as possible. The diagram below gives the rough relationships between the modules:

![Object Diagram](docs/class-diagram.png)

Each of the blocks depicted will now be examined in detail.

### Service - service.py

Service is the top level module, and is responsible for bootstrapping the rest of the program. As such it is very simple - it merely instantiates instances or the driver, the router and the web server and sets up connections between them.

### Web API

This block is an external dependency on the NMOS Common Web API class. It is responsible for running the HTTP server that presents the API externally, managing connections, etc. It is based on Python Flask, and much of its operation will be familiar to users of Flask. As one of its arguments it accepts an instance of the router class, which defines methods for handling requests to the server.

### Router - router.py
This block is the "top level" of the API itself, and defines the routing behaviour of the API. This is therefore a good starting point when trying to trace which sections of code are responding to calls made to the API. The driver may ask the router to invoke new sender and receiver representations, which are then made available through the API. In order to serve requests this block makes calls out to sender and receiver implementations and their associated activators and transport file managers.

### Sender and Receiver Representations
These blocks are the data representations of the senders and receivers of the API. They are responsible for the validation of requests relating to the staging of parameters, and store the current staged and active parameters associated with that sender or receiver. The Connection Management API allows for senders and receivers based on various transport mechanisms, e.g RTP or DASH. As such it is possible to have more than on implementation of these blocks, which may be used interchangeably within the same instance of the API. To ensure a consistent interface for all implementations of of the senders and receivers all implementations must be of the AbstractDevice class contained in activator.py.

At the time of writing the reference implementation only contains RTP implementations of the senders and receivers, which are contained in rtpReceiver.py and rtpSender.py respectively.

### Activator - activator.py
This block is responsible for handling any requests to the API to do with activation (e.g anything sent to a /activate endpoint). There are multiple instances of this class within the API, each assigned to either a sender and receiver. Each activator will only handle activation requests for the sender or receiver it is assigned to. In the case of immediate activations it will call the activate method on its sender or receiver immediately. In the case of a scheduled activation this class is responsible for ensuring the timing of the activation, and will call the activate method on the sender or receiver at the right time.

### Driver
The driver block is responsible for communication with the actual device/s being controlled by the API. As a vast array of different devices with different native control interfaces may be controlled by the API it is possible to have multiple implementations of the driver within the same instance of the API. The driver is responsible to alerting the router to new senders or receivers, and their initial parameters. The driver must also alert the router when senders and receivers cease to exits. Furthermore when sender and receiver parameters are activated the sender or receiver class will call a method on their corresponding driver, so that the parameters may be communicated to the device via the driver.

## Tests

Each module has a set of unit tests implemented using the Python Unit Testing Framework, and may be ran in the usual manner:

`python -m unittest discover`

Test scripts for a given module are named test<module name>.py.

function doInit(){
    senderUpdate()
    receiverUpdate()
}

function addSender(){
    dropdown = document.getElementById('sender-legs');
    request = {}
    request['legs'] = dropdown.options[dropdown.selectedIndex].text;
    request['fec'] = document.getElementById('sender-fec').checked
    request['rtcp'] = document.getElementById('sender-rtcp').checked
    doPost(request, "api/senders/", senderUpdate);
}

function addReceiver(){
    dropdown = document.getElementById('receiver-legs');
    request = {}
    request['legs'] = dropdown.options[dropdown.selectedIndex].text;
    request['fec'] = document.getElementById('receiver-fec').checked
    request['rtcp'] = document.getElementById('receiver-rtcp').checked
    doPost(request, "api/receivers/", receiverUpdate);
}

function senderUpdate(){
    doGet('api/senders/', updateSenderTable);
}

function receiverUpdate(){
    doGet('api/receivers/', updateReceiverTable);
}

function doPost(request, url, callback){
    http = new XMLHttpRequest();
    http.open("POST", url, true);
    http.setRequestHeader("Content-type", "application/json");
    http.onreadystatechange = function(){
        if(http.readyState == 4 && http.status == 200){
            callback()
        }
    }
    http.send(JSON.stringify(request, null, 2));
}

function doGet(url, callback){
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() { 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback(JSON.parse(xmlHttp.responseText));
    }
    xmlHttp.open("GET", url, true);
    xmlHttp.send(null);
}

function doDelete(url, callback){
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() { 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback();
    }
    xmlHttp.open("DELETE", url, true);
    xmlHttp.send(null);
}

function updateSenderTable(portList){
    updateTable('senders', portList);
}

function updateReceiverTable(portList){
    updateTable('receivers', portList);
}

function updateTable(type, portList){
    new_tbody = document.createElement('tbody')
    table = document.getElementById(type + '-table');
    table.replaceChild(new_tbody, table.getElementsByTagName('tbody')[0]);
    console.log(portList)
    console.log(type)
    portList.forEach(function(entry, index){
        url = 'api/' + type + '/' + entry + '/'
        doGet(url, function(port){
            addTableRow(port, entry, index, type);
        })
    });
}

function addTableRow(port, uuid, count, type){
    console.log(port)
    console.log(type)
    table = document.getElementById(type + '-table');
    tbody = table.getElementsByTagName('tbody')[0]
    row = tbody.insertRow(0)
    uuidCell = row.insertCell(0);
    legCell = row.insertCell(1);
    fecCell = row.insertCell(2);
    rtcpCell = row.insertCell(3);
    binCell = row.insertCell(4);
    legCell.innerHTML = port['legs']
    uuidCell.innerHTML = uuid
    if(port['fec']){
        span = document.createElement("span")
        span.classList.add("glyphicon")
        span.classList.add("glyphicon-ok")
        fecCell.appendChild(span)
    }
    if(port['rtcp']){
        span = document.createElement("span")
        span.classList.add("glyphicon")
        span.classList.add("glyphicon-ok")
        rtcpCell.appendChild(span)
    }
    span = document.createElement("span")
    span.classList.add("glyphicon")
    span.classList.add("glyphicon-trash")
    span.classList.add("delete-button")
    span.onclick = function(){
        deleteCallback(type, uuid)
    }
    binCell.appendChild(span)
}



function deleteCallback(type, uuid){
    doDelete('api/' + type + '/' + uuid + '/', function(){
        if(type == "senders"){
            callback = updateSenderTable;
        }else{
            callback = updateReceiverTable;
        }
        doGet('api/' + type + '/', callback)
    })
}

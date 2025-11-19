function connect(){

    let formData = new FormData();
    formData.append('uart', $('#uart').val());
    formData.append('elfFile', $('#elfFile')[0].files[0]);

    $.ajax({
        url: '/connect',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.status === 'success') {
                setConnectState(true);
            }
        },
        error: function(data) {
            alert(data.responseJSON.msg);
            setConnectState(false);
        }
    });

    $("#btnConnect").prop("disabled", true);
    $("#btnConnect").html("Loading...");
}

function disconnect(){
    $.getJSON('/disconnect', function(data) {
        setConnectState(false);
    });
}

function load_uart() {
    $.getJSON('/serial-ports', function(data) {
        uart = $('#uart');
        uart.empty();
        uart.append('<option value="default">Select UART</option>');
        data.forEach(function(item) {
            uart.append($('<option></option>').val(item).html(item));
        });
    });
}

function setConnectState(status) {
    if(status) {
        parameterCardEnabled = true;
        scopeCardEnabled = true;
        $('#setupView').addClass('collapse');
        $('#watchView').removeClass('disabled');
        $('#scopeView').removeClass('disabled');
        $("#btnWatchView").prop("disabled", false);
        $("#btnScopeView").prop("disabled", false);
        $("#btnConnect").prop("disabled", true);
        $("#btnConnect").html("Disconnect", true);
        $('#connection-status').html('Connected');

    }
    else {
        parameterCardEnabled = false;
        scopeCardEnabled = false;
        $('#setupView').removeClass('collapse');
        $('#watchView').addClass('disabled');
        $('#scopeView').addClass('disabled');
        $("#btnConnect").prop("disabled", false);
        $('#connection-status').html('Disconnected');
        $('#btnConnect').html('Connect');
        $('#btnConnect').removeClass('btn-danger');
        $('#btnConnect').addClass('btn-primary');
        $('#setupView').removeClass('disabled');
    }
}

function initSetupCard(){
    $('#update_com_port').on('click', load_uart);
    $('#btnConnect').on('click', function() {
        if($('#btnConnect').html() === "Connect") connect();
        else disconnect();
    });
    $('#connection-status').on('click', function() {
        if($('#connection-status').html() === "Disconnected") connect();
        else disconnect();
    });
}

function insertQRCode(link) {
    qrCodeHtml = "<form id='ipForm'> \
        <label for='ipAddress'>Enter local IP address:</label> \
        <input type='text' id='ipAddress' name='ipAddress' placeholder='192.168.1.1'> \
        <button id='updateButton'>Update</button> \
        </form><div id='qrcode'></div>";

    $('#x2cModalBody').empty();
    $('#x2cModalBody').html(qrCodeHtml);

    new QRCode(document.getElementById("qrcode"), "http://0.0.0.0:5000/" + link);

    $('#updateButton').click(function(e) {
        e.preventDefault(); // Prevent the default form submit action
        var ipAddress = $('#ipAddress').val();
        var ipFormat = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
        if(ipFormat.test(ipAddress)) {
            $("#qrcode").empty();
            new QRCode(document.getElementById("qrcode"), "http://" + ipAddress + ":5000/" + link);
        } else {
            alert('Invalid IP address format.');
        }
    });
}

function initQRCodes() {

    $("#watchQRCode").on("click", function() {
        $('#x2cModalTitle').html('WatchView - Scan QR Code');
        insertQRCode("watch-view");
        $('#x2cModal').modal('show');
    });
    $("#scopeQRCode").on("click", function() {
        $('#x2cModalTitle').html('ScopeView - Scan QR Code');
        insertQRCode("scope-view");
        $('#x2cModal').modal('show');
    });
}

$(document).ready(function() {
    initSetupCard();
    load_uart();
    initQRCodes();

    // Toggles for views
    const toggleWatch = document.getElementById('toggleWatch');
    const toggleScope = document.getElementById('toggleScope');
    const watchCol = document.getElementById('watchCol');
    const scopeCol = document.getElementById('scopeCol');

    // Mobile view (tabs)
    // Mobile tab click handlers
    document.getElementById('tabWatch').addEventListener('click', function() {
        watchCol.classList.remove('d-none');
        scopeCol.classList.add('d-none');
        this.classList.add('active');
        document.getElementById('tabScope').classList.remove('active');
    });

    document.getElementById('tabScope').addEventListener('click', function() {
        watchCol.classList.add('d-none');
        scopeCol.classList.remove('d-none');
        this.classList.add('active');
        document.getElementById('tabWatch').classList.remove('active');
    });

    // Desktop view (toggles)
    // Uncheck toggles and hide views by default on desktop
    toggleWatch.checked = false;
    toggleScope.checked = false;
    watchCol.classList.add('d-none');
    scopeCol.classList.add('d-none');

    // Update toggle button states
    document.querySelector('label[for="toggleWatch"]').classList.remove('active');
    document.querySelector('label[for="toggleScope"]').classList.remove('active');

    // Toggle event listeners for desktop
    toggleWatch.addEventListener('change', () => {
        watchCol.classList.toggle('d-none', !toggleWatch.checked);
        document.querySelector('label[for="toggleWatch"]').classList.toggle('active', toggleWatch.checked);
    });

    toggleScope.addEventListener('change', () => {
        scopeCol.classList.toggle('d-none', !toggleScope.checked);
        document.querySelector('label[for="toggleScope"]').classList.toggle('active', toggleScope.checked);
    });

    $.getJSON('/is-connected', function(data) {
        setConnectState(data.status);
    });

});
function connect(){

    let formData = new FormData();
    const interfaceType = $('#interfaceType').val();
    formData.append('interfaceType', interfaceType);

    if (interfaceType === 'SERIAL') {
        formData.append('interfaceArgument', 'port');
        formData.append('interfaceValue', $('#port').val());
    }
    else if (interfaceType === 'TCP_IP') {
        formData.append('host', $('#host').val());
        formData.append('tcpPort', $('#tcpPort').val());
    }
    else if (interfaceType === 'CAN') {
        formData.append('canBusType', $('#canBusType').val());
        formData.append('canChannel', $('#canChannel').val());
        formData.append('canBaudrate', $('#canBaudrate').val());
        formData.append('canMode', $('#canMode').val());
        formData.append('canTxId', $('#canTxId').val());
        formData.append('canRxId', $('#canRxId').val());
    }

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
        uart = $('#port');
        uart.empty();
        uart.append('<option value="default">Select UART</option>');
        data.forEach(function(item) {
            uart.append($('<option></option>').val(item).html(item));
        });
    });
}

function setInterfaceSetupFields() {
    const interfaceType = $('#interfaceType').val();

    $('#uartRow').addClass('d-none');
    $('#hostRow').addClass('d-none');
    $('#canRow').addClass('d-none');

    if (interfaceType === 'SERIAL') {
        $('#uartRow').removeClass('d-none');
        load_uart();
    }
    else if (interfaceType === 'TCP_IP') {
        $('#hostRow').removeClass('d-none');
    }
    else if (interfaceType === 'CAN') {
        $('#canRow').removeClass('d-none');
    }
}

function setConnectState(status) {
    if(status) {
        parameterCardEnabled = true;
        scopeCardEnabled = true;
        $('#setupView').addClass('collapse');
        $('#watchView').removeClass('disabled');
        $('#scopeView').removeClass('disabled');
        $('#dashboardView').removeClass('disabled');
        $("#btnWatchView").prop("disabled", false);
        $("#btnScopeView").prop("disabled", false);
        $("#btnDashboardView").prop("disabled", false);
        $("#btnConnect").prop("disabled", true);
        $("#btnConnect").html("Disconnect", true);
        $('#connection-status').html('Connected');
        $('#desktopTabs').removeClass('disabled');
        $('#mobileTabs').removeClass('disabled');

    }
    else {
        parameterCardEnabled = false;
        scopeCardEnabled = false;
        $('#setupView').removeClass('collapse');
        $('#watchView').addClass('disabled');
        $('#scopeView').addClass('disabled');
        $('#dashboardView').addClass('disabled');
        $("#btnConnect").prop("disabled", false);
        $('#connection-status').html('Disconnected');
        $('#btnConnect').html('Connect');
        $('#btnConnect').removeClass('btn-danger');
        $('#btnConnect').addClass('btn-primary');
        $('#setupView').removeClass('disabled');
        $('#desktopTabs').addClass('disabled');
        $('#mobileTabs').addClass('disabled');
    }
}

function initSetupCard(){
    $('#update_com_port').on('click', load_uart);
    $('#interfaceType').on('change', setInterfaceSetupFields);
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
        insertQRCode("watch");
        $('#x2cModal').modal('show');
    });
    $("#scopeQRCode").on("click", function() {
        $('#x2cModalTitle').html('ScopeView - Scan QR Code');
        insertQRCode("scope");
        $('#x2cModal').modal('show');
    });
    $("#dashboardQRCode").on("click", function() {
        $('#x2cModalTitle').html('Dashboard - Scan QR Code');
        insertQRCode("dashboard");
        $('#x2cModal').modal('show');
    });
    $("#scriptQRCode").on("click", function() {
        $('#x2cModalTitle').html('Script - Scan QR Code');
        insertQRCode("scripting");
        $('#x2cModal').modal('show');
    });
}

$(document).ready(function() {
    initSetupCard();
    setInterfaceSetupFields();
    initQRCodes();

    // Toggles for views
    const toggleWatch = document.getElementById('toggleWatch');
    const toggleScope = document.getElementById('toggleScope');
    const toggleDashboard = document.getElementById('toggleDashboard');
    const toggleScript = document.getElementById('toggleScript');
    const watchCol = document.getElementById('watchCol');
    const scopeCol = document.getElementById('scopeCol');
    const dashboardCol = document.getElementById('dashboardCol');
    const scriptCol = document.getElementById('scriptCol');

    // Mobile view (tabs)
    // Mobile tab click handlers
    document.getElementById('tabWatch').addEventListener('click', function() {
        watchCol.classList.remove('d-none');
        scopeCol.classList.add('d-none');
        dashboardCol.classList.add('d-none');
        scriptCol.classList.add('d-none');
        this.classList.add('active');
        document.getElementById('tabScope').classList.remove('active');
        document.getElementById('tabDashboard').classList.remove('active');
        document.getElementById('tabScript').classList.remove('active');
    });

    document.getElementById('tabScope').addEventListener('click', function() {
        watchCol.classList.add('d-none');
        scopeCol.classList.remove('d-none');
        dashboardCol.classList.add('d-none');
        scriptCol.classList.add('d-none');
        this.classList.add('active');
        document.getElementById('tabWatch').classList.remove('active');
        document.getElementById('tabDashboard').classList.remove('active');
        document.getElementById('tabScript').classList.remove('active');
    });

    document.getElementById('tabDashboard').addEventListener('click', function() {
        scopeCol.classList.add('d-none');
        watchCol.classList.add('d-none');
        dashboardCol.classList.remove('d-none');
        scriptCol.classList.add('d-none');
        this.classList.add('active');
        document.getElementById('tabWatch').classList.remove('active');
        document.getElementById('tabScope').classList.remove('active');
        document.getElementById('tabScript').classList.remove('active');
    });

    document.getElementById('tabScript').addEventListener('click', function() {
        scopeCol.classList.add('d-none');
        watchCol.classList.add('d-none');
        dashboardCol.classList.add('d-none');
        scriptCol.classList.remove('d-none');
        this.classList.add('active');
        document.getElementById('tabWatch').classList.remove('active');
        document.getElementById('tabScope').classList.remove('active');
        document.getElementById('tabDashboard').classList.remove('active');
    });

    // Hide all view cards by default - only setup card is visible
    toggleWatch.checked = false;
    toggleScope.checked = false;
    toggleDashboard.checked = false;
    toggleScript.checked = false;
    watchCol.classList.add('d-none');
    scopeCol.classList.add('d-none');
    dashboardCol.classList.add('d-none');
    scriptCol.classList.add('d-none');

    // Update toggle button states
    document.querySelector('label[for="toggleWatch"]').classList.remove('active');
    document.querySelector('label[for="toggleScope"]').classList.remove('active');
    document.querySelector('label[for="toggleDashboard"]').classList.remove('active');
    document.querySelector('label[for="toggleScript"]').classList.remove('active');

    // Toggle event listeners for desktop
    toggleWatch.addEventListener('change', () => {
        watchCol.classList.toggle('d-none', !toggleWatch.checked);
        document.querySelector('label[for="toggleWatch"]').classList.toggle('active', toggleWatch.checked);
    });

    toggleScope.addEventListener('change', () => {
        scopeCol.classList.toggle('d-none', !toggleScope.checked);
        document.querySelector('label[for="toggleScope"]').classList.toggle('active', toggleScope.checked);
    });

    toggleDashboard.addEventListener('change', () => {
        dashboardCol.classList.toggle('d-none', !toggleDashboard.checked);
        document.querySelector('label[for="toggleDashboard"]').classList.toggle('active', toggleDashboard.checked);
    });

    toggleScript.addEventListener('change', () => {
        scriptCol.classList.toggle('d-none', !toggleScript.checked);
        document.querySelector('label[for="toggleScript"]').classList.toggle('active', toggleScript.checked);
    });

    $.getJSON('/is-connected', function(data) {
        setConnectState(data.status);
    });

});
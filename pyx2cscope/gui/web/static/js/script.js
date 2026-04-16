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
    $.getJSON('/disconnect', function() {
        setConnectState(false);
    });
}

function exportVariables() {
    const exportToggle = $('#exportVariablesToggle');
    if (exportToggle.attr('aria-disabled') === 'true') {
        return;
    }

    $('#x2cModalTitle').html('Export Variables');
    $('#x2cModalBody').html(`
        <p>Export the variables currently used in Watch View, Scope View, and Dashboard.</p>
        <div class="d-flex gap-2 justify-content-center">
            <a class="btn btn-primary" href="/variables/export?ext=yml">Export YML</a>
            <a class="btn btn-outline-primary" href="/variables/export?ext=pkl">Export PKL</a>
        </div>
    `);
    $('#x2cModal').modal('show');
}

function load_uart() {
    $.getJSON('/serial-ports', function(data) {
        uart = $('#port');
        uart.empty();
        // Add AUTO option as default selection
        uart.append($('<option selected></option>').val('AUTO').html('AUTO (Auto-detect)'));
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
        $('#exportVariablesToggle').removeClass('disabled text-white-50').attr('aria-disabled', 'false');
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
        $('#exportVariablesToggle').addClass('disabled text-white-50').attr('aria-disabled', 'true');
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
    $('#exportVariablesToggle').on('click', function(e) {
        e.preventDefault();
        exportVariables();
    });

    $('#connection-status').on('click', function() {
        if($('#connection-status').html() === "Disconnected") connect();
        else disconnect();
    });
}

function insertQRCode(link) {
    qrCodeHtml = `
        <div class="mb-3">
            <h6>Instructions</h6>
            <ol class="small text-muted">
                <li>Ensure your mobile device is connected to the same network as this host.</li>
                <li>The server must be started with shared access: <code>--host 0.0.0.0</code></li>
                <li>Select your host's IP address below or enter a custom one.</li>
                <li>Scan the QR code with your mobile device to open the page.</li>
            </ol>
        </div>
        <form id='ipForm'>
            <div class="mb-3">
                <label for='ipSelect' class="form-label">Select Host IP Address:</label>
                <select id='ipSelect' class="form-select">
                    <option value="">Loading available IPs...</option>
                </select>
            </div>
            <div class="mb-3">
                <label for='ipAddress' class="form-label">Or enter custom IP:</label>
                <input type='text' id='ipAddress' class="form-control" name='ipAddress' placeholder='192.168.1.1'>
            </div>
            <button id='updateButton' class="btn btn-primary">Generate QR Code</button>
        </form>
        <div id='qrcode' class='mt-3 text-center'></div>
    `;

    $('#x2cModalBody').empty();
    $('#x2cModalBody').html(qrCodeHtml);

    // Load available IP addresses
    $.getJSON('/local-ips', function(data) {
        const ipSelect = $('#ipSelect');

        ipSelect.empty();
        if (data.ips && data.ips.length > 0) {
            data.ips.forEach(function(ip) {
                ipSelect.append($('<option></option>').val(ip).text(ip));
            });
            // Generate initial QR code with first IP
            new QRCode(document.getElementById("qrcode"), "http://" + data.ips[0] + ":5000/" + link);
        } else {
            ipSelect.append($('<option></option>').val('').text('No IPs found - enter manually'));
            new QRCode(document.getElementById("qrcode"), "http://0.0.0.0:5000/" + link);
        }
    }).fail(function() {
        // Fallback if endpoint doesn't exist
        $('#ipSelect').empty().append($('<option></option>').val('0.0.0.0').text('0.0.0.0 (default)'));
        new QRCode(document.getElementById("qrcode"), "http://0.0.0.0:5000/" + link);
    });

    // Update QR code when IP is selected from dropdown
    $(document).on('change', '#ipSelect', function() {
        const selectedIp = $(this).val();
        if (selectedIp) {
            $("#qrcode").empty();
            new QRCode(document.getElementById("qrcode"), "http://" + selectedIp + ":5000/" + link);
        }
    });

    // Update QR code when custom IP is entered
    $(document).on('click', '#updateButton', function(e) {
        e.preventDefault();
        var ipAddress = $('#ipAddress').val();
        var ipFormat = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
        if (ipAddress && ipFormat.test(ipAddress)) {
            $("#qrcode").empty();
            new QRCode(document.getElementById("qrcode"), "http://" + ipAddress + ":5000/" + link);
        } else if (ipAddress) {
            alert('Invalid IP address format.');
        } else {
            // Use selected IP from dropdown
            const selectedIp = $('#ipSelect').val();
            if (selectedIp) {
                $("#qrcode").empty();
                new QRCode(document.getElementById("qrcode"), "http://" + selectedIp + ":5000/" + link);
            }
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
    $("#mainPageQRCode").on("click", function() {
        $('#x2cModalTitle').html('Main Page - Scan QR Code');
        insertQRCode("");
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
    $("#mainPageQRCode").on("click", function() {
        $('#x2cModalTitle').html('Main Page - Scan QR Code');
        insertQRCode("");
        $('#x2cModal').modal('show');
    });
}

function initHelpToggle() {
    const helpToggle = document.getElementById('helpToggle');
    const welcomeCard = document.getElementById('welcomeCard');

    if (helpToggle && welcomeCard) {
        helpToggle.addEventListener('click', function(e) {
            e.preventDefault();
            welcomeCard.classList.toggle('d-none');
        });
    }
}

function initHelpToggle() {
    const helpToggle = document.getElementById('helpToggle');
    const welcomeCard = document.getElementById('welcomeCard');

    if (helpToggle && welcomeCard) {
        helpToggle.addEventListener('click', function(e) {
            e.preventDefault();
            welcomeCard.classList.toggle('d-none');
        });
    }
}

$(document).ready(function() {
    initSetupCard();
    setInterfaceSetupFields();
    initQRCodes();
    initHelpToggle();

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

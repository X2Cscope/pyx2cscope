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
                $("#btnConnSetup").click();
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
        $('#watchView').removeClass('disabled');
        $('#scopeView').removeClass('disabled');
        $("#btnWatchView").prop("disabled", false);
        $("#btnScopeView").prop("disabled", false);
        $("#btnConnect").prop("disabled", false);
        $('#btnConnect').html('Disconnect');
        $('#btnConnect').removeClass('btn-primary');
        $('#btnConnect').addClass('btn-danger');
    }
    else {
        parameterCardEnabled = false;
        scopeCardEnabled = false;
        $('#watchView').addClass('disabled');
        $('#scopeView').addClass('disabled');
        $("#btnConnect").prop("disabled", false);
        $('#btnConnect').html('Connect');
        $('#btnConnect').removeClass('btn-danger');
        $('#btnConnect').addClass('btn-primary');
    }
}

function initSetupCard(){
    $('#update_com_port').on('click', load_uart);
    $('#btnConnect').on('click', function() {
        if($('#btnConnect').html() === "Connect") connect();
        else disconnect();
    });
}

$(document).ready(function() {
    initSetupCard();
    load_uart();

//    $("#btnWatchView").prop("disabled",true);
//    $("#btnScopeView").prop("disabled",true);
//
//    $.getJSON('/is-connected', function(data) {
//        setConnectState(data.status);
//        if(data.status == false)
//           $("#btnConnSetup").click();
//    });
});
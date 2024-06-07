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
                parameterCardEnabled = true;
                scopeCardEnabled = true;
                $('#parameterCard').removeClass('disabled');
                $('#scopeCard').removeClass('disabled');
                $('#connect').html('Disconnect');
            } else {
                alert(response.status);
            }
        },
        error: function() {
            alert('Please select the UART and upload a .elf file.');
        }
    });
}

function disconnect(){
    $.getJSON('/disconnect', function(data) {
        parameterCardEnabled = false;
        scopeCardEnabled = false;
        $('#parameterCard').addClass('disabled');
        $('#scopeCard').addClass('disabled');
        $('#connect').html('Connect');
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

function initSetupCard(){
    $('#update_com_port').on('click', load_uart);
    $('#connect').on('click', function() {
        if($('#connect').html() === "Connect") connect();
        else disconnect();
    });
}

$(document).ready(function() {
    initSetupCard();
    load_uart();
});
let parameterCardEnabled = false;
let scopeCardEnabled = false;

function update_scope_data() {

    if (scopeCardEnabled) {
        $.getJSON('/scope', function(data) {
            let tableRows = '';
            data.forEach(function(item) {
                tableRows += `<tr><td>${item.time}</td><td>${item.value}</td><td><input type="checkbox" class="scope-checkbox" data-time="${item.time}" data-value="${item.value}"></td></tr>`;
            });
            $('#scopeTable tbody').html(tableRows);
            updateChart();
        });
    }
}

function update_parameter_data()
{
    if (parameterCardEnabled) {
        $.getJSON('/data', function(data) {
            let tableRows = '';
            data.forEach(function(item) {
                tableRows += `
                    <tr class="rowClass">
                        <td class="rowIndex">${item.param}</td>
                        <td contenteditable="true">${item.value}</td>
                        <td class="text-center">
                            <button class="btn btn-danger remove" type="button">Remove</button>
                        </td>
                    </tr>`;
            });
            $('#parameterTable tbody').html(tableRows);
        });
    }
}

function setParameterRefreshInterval(){

    let parameterRefreshInterval;

    // Handle the Refresh button click
    $('#paramRefresh').click(function() {
        update_parameter_data();
    });

    // Handle the dropdown items click
    $('#refreshNow').click(function() {
        update_parameter_data();
    });

    $('#refresh1s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(update_parameter_data, 1000);
    });

    $('#refresh3s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(update_parameter_data, 3000);
    });

    $('#refresh5s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(update_parameter_data, 5000);
    });

    $('#stopRefresh').click(function() {
        clearInterval(parameterRefreshInterval);
    });
}

function updateChart() {
    let selectedData = [];
    $('.scope-checkbox:checked').each(function() {
        selectedData.push({
            time: $(this).data('time'),
            value: $(this).data('value')
        });
    });

    let ctx = document.getElementById('scopeChart').getContext('2d');
    let chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: selectedData.map(d => d.time),
            datasets: [{
                label: 'Scope Data',
                data: selectedData.map(d => d.value),
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
                fill: false
            }]
        },
        options: {
            scales: {
                xAxes: [{
                    type: 'linear',
                    position: 'bottom'
                }]
            }
        }
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

function load_actions() {
    $('#update_com_port').on('click', load_uart);
    $('#connect').on('click', function() {
        if($('#connect').html() === "Connect") connect();
        else disconnect();
    });
    parameterSearch();
    setParameterTableListeners();
    setParameterRefreshInterval();
     $('#parameterTable').on('blur', 'td[contenteditable="true"]', function() {
        // Call your getJSON function here
        parameter = $(this).siblings()[0].textContent;
        parameter_value = $(this).html();
        $.getJSON('/update-parameter-value',
        {
            param: parameter,
            value: parameter_value
        });
    });
    // edit the number when on focus
    $('#parameterTable').on('keypress', 'td[contenteditable="true"]', function(e) {
        // Replace non-digit characters with an empty string
        if (e.which === 13) {
            $(this).blur(); // Remove focus from the current contenteditable element
            return false;
        }
        if ((e.which != 46 || $(this).val().indexOf('.') != -1) && (e.which < 48 || e.which > 57)) {
            return false;
        }
    });
}

function setParameterTableListeners(){

    // edit cell
    $('table td').change(function () {
        alert("blur new value : "+$(this).text());
    });

    // delete Row
    $('#parameterTableBody').on('click', '.remove', function () {

        parameter = $(this).parent().siblings()[0].textContent;
        $.getJSON('/delete-parameter-search',
        {
            param: parameter
        },
        function(data) {
            update_parameter_data();
        });
        //$(this).parent('td.text-center').parent('tr.rowClass').remove();
    });
}

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
            alert('Please select Local UART and upload a .hex file.');
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

function parameterSearch(){
    $('#parameterSearch').select2({
        placeholder: "Select a variable",
        allowClear: true,
        ajax: {
            url: 'variables',
            dataType: 'json',
            delay: 250,
            processResults: function (data) {
                return {
                    results: data.items
                };
            },
            cache: true
        },
        minimumInputLength: 3
    });

    $('#parameterSearch').on('select2:select', function(e){
        parameter = $('#parameterSearch').select2('data')[0]['text'];
        $.getJSON('/add-parameter-search',
        {
            param: parameter
        },
        function(data) {
            $('#parameterSearch').val(null).trigger('change');
            update_parameter_data();
        });
    });
}

function parameterSearch(){
    $('#scopeSearch').select2({
        placeholder: "Select a variable",
        allowClear: true,
        ajax: {
            url: 'variables',
            dataType: 'json',
            delay: 250,
            processResults: function (data) {
                return {
                    results: data.items
                };
            },
            cache: true
        },
        minimumInputLength: 3
    });

    $('#scopeSearch').on('select2:select', function(e){
        parameter = $('#scopeSearch').select2('data')[0]['text'];
        $.getJSON('/add-scope-search',
        {
            param: parameter
        },
        function(data) {
            $('#scopeSearch').val(null).trigger('change');
            update_scope_data();
        });
    });
}

$(document).ready(function() {

    load_actions();
    load_uart();
    update_scope_data();

});
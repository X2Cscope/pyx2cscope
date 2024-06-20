let scopeCardEnabled = true;
let dataReadyInterval;
let scopeTable;
let scopeChart;

function initScopeSelect(){
    $('#scopeSearch').select2({
        placeholder: "Select a variable",
        dropdownAutoWidth : true,
        allowClear: true,
        ajax: {
            url: '/variables',
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
        $.getJSON('/scope-view/add',
        {
            param: parameter
        },
        function(data) {
            $('#scopeSearch').val(null).trigger('change');
            scopeTable.ajax.reload();
        });
    });
}

function sv_remove_chart_data(parameter) {
    scopeChart.data.labels.pop(parameter);
    scopeChart.data.datasets.forEach((dataset) => {
        if(dataset.data.id == parameter) dataset.data.pop();
    });
    scopeChart.update();
}

function setScopeTableListeners(){
    // delete Row on button click
    $('#scopeTableBody').on('click', '.remove', function () {
        parameter = $(this).parent().siblings()[2].textContent;
        $.getJSON('/scope-view/remove',
        {
            param: parameter
        },
        function(data) {
            scopeTable.ajax.reload();
            sv_remove_chart_data(parameter);
        });
    });

    // update variable after loosing focus on element
    $('#scopeTable').on('blur', 'td[contenteditable="true"]', function(){
        sv_update_param(this);
    });

    // edit the number when on focus
    $('#scopeTable').on('keypress', 'td[contenteditable="true"]', function(e) {
        // Replace non-digit characters with an empty string
        if (e.which === 13) {
            $(this).blur(); // Remove focus from the current contenteditable element
            return false;
        }
         if ((e.which != 45 || $(this).val().indexOf('-') != -1)
            && (e.which != 46 || $(this).val().indexOf('.') != -1)
            && (e.which < 48 || e.which > 57)) {
            return false;
        }
//        const regex = /[+-]?([0-9]{1,}[.])[0-9]+/;
//        if(!regex.test($(this).val()))
//        {
//            return false;
//        }
    });
}

function sv_update_param(element) {
    parameter = $(element).closest("tr").children()[2].textContent;
    index = $(element).closest("td").index();
    parameter_field = $("#scopeTable thead>tr").children()[index].textContent;

    if(element.contentEditable == "true")
    {
        parameter_value = $(element).html();
    }
    else // checkbox, color
    {
        if(element.type == "checkbox") parameter_value = element.checked? "1":"0";
        if(element.type == "color") parameter_value = element.value;
    }

    $.getJSON('/scope-view/update',
    {
        param: parameter,
        field: parameter_field,
        value: parameter_value
    }, function (data){
        scopeTable.ajax.reload();
    });
}

function sv_update_scope_data(data) {
    scopeChart.data.datasets = data.data;
    scopeChart.data.labels = data.labels;
    scopeChart.update('none');
}

function initScopeCard(){
    initScopeSelect();
    setScopeTableListeners();
}

function sv_checkbox(data, type) {
    val = '<input type="checkbox" onclick="sv_update_param(this);"';
    if(data) val += ' checked="checked"';
    return val += '>';
}

function sv_color(data, type) {
    val = '<input type="color" onchange="sv_update_param(this);"';
    val += ' value="' + data + '">';
    return val;
}

function sv_remove(data, type){
    return '<button class="btn btn-danger remove" type="button">Remove</button>';
}

const zoomOptions = {
    pan: {
        enabled: true,
        modifierKey: 'ctrl',
    },
    zoom: {
        drag: {
            enabled: true,
        },
        wheel: {
            enabled: false,
        },
        pinch: {
            enabled: true
        },
        mode: 'xy'
    }
}

function initScopeChart() {
    let ctx = document.getElementById('scopeChart').getContext('2d');
    scopeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
            datasets: [{
                label: 'Empty Dataset',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Time (ms)'
                    }
                },
            },
            plugins: {
                zoom: zoomOptions,
            }
        }
    });

    $('#chartZoomReset').on('click', function() {
        scopeChart.resetZoom();
    });

    $('#chartExport').attr("href", "/scope-view/export")
}

function sv_clear_stop_focus() {
    $("#triggerStop").removeClass("active");
    $("#triggerStop").removeClass("focus");
}

function sv_set_stop_focus() {
    sampleTriggerButtons = document.querySelectorAll('input[name="triggerAction"]');
    sampleTriggerButtons.forEach(button => {
        if(button.id == "triggerStop") {
            button.parentElement.classList.add("active");
            button.parentElement.classList.add("focus");
        }
        else {
            button.parentElement.classList.remove("active");
            button.parentElement.classList.remove("focus");
        }
    });
}

function sv_data_ready_check()
{
    $.getJSON('/scope-view/chart', function(data) {
        if(data.finish) {
            sv_set_stop_focus();
            sv_update_scope_data(data);
        }
        else {
            if(data.ready) sv_update_scope_data(data);
            if(dataReadyInterval) setTimeout(sv_data_ready_check, 200);
        }
    });
}

function initScopeForms(){
    $("#sampleControlForm").submit(function(e) {
        e.preventDefault(); // avoid to execute the actual submit of the form.
        var form = $(this);

        $.ajax({
            type: "POST",
            url: "/scope-view/form-sample",
            data: form.serialize(),
            success: function(data)
            {
                if(data.trigger){
                    dataReadyInterval = true;
                    setTimeout(sv_data_ready_check, 200);
                    sv_clear_stop_focus();
                }
                else {
                    dataReadyInterval = false;
                }
            }
        });
    });

    sampleTriggerButtons = document.querySelectorAll('input[name="triggerAction"]');
    sampleTriggerButtons.forEach(button => {
        button.addEventListener('click', function() {
            $("#sampleControlForm").submit();
        });
    });

    $("#triggerControlForm").submit(function(e) {
        e.preventDefault(); // avoid to execute the actual submit of the form.
        var form = $(this);

        $.ajax({
            type: "POST",
            url: "/scope-view/form-trigger",
            data: form.serialize(), // serializes the form's elements.
            success: function(data){
            }
        });
    });

    $("#scopeSave").attr("href", "/scope-view/save");
    $("#scopeLoad").on("change", function(event) {
        var file = event.target.files[0];
        var formData = new FormData();
        formData.append('file', file);

        $.ajax({
            url: '/scope-view/load', // Replace with your server upload endpoint
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                scopeTable.ajax.reload();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                alert(jqXHR.responseJSON.msg);
            }
        }).always(function() {
            $("#scopeLoad").val("");
        });
    });
}

$(document).ready(function () {
    initScopeSelect();
    setScopeTableListeners();
    initScopeForms();
    initScopeChart();

    scopeTable = $('#scopeTable').DataTable({
        ajax: '/scope-view/data',
        searching: false,
        paging: false,
        info: false,
        columns: [
            {data: 'trigger', render: sv_checkbox},
            {data: 'enable', render: sv_checkbox},
            {data: 'variable'},
            {data: 'color', render: sv_color, orderable: false},
            {data: 'gain', orderable: false},
            {data: 'offset', orderable: false},
            {data: 'remove', render: sv_remove, orderable: false}
        ],
        columnDefs: [
            {
                targets: [, 4, 5],
                "createdCell": function (td, cellData, rowData, row, col) {
                    $(td).attr('contenteditable', 'true');
                }
            }
        ]
    });
});
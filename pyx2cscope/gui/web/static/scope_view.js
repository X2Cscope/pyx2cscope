let scopeCardEnabled = true;
let dataReadyRefreshInterval;
let scopeTable;
let scopeChart;

function initScopeSelect(){
    $('#scopeSearch').select2({
        placeholder: "Select a variable",
        dropdownAutoWidth : true,
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
    chart.data.datasets.forEach((dataset) => {
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
        if ((e.which != 46 || $(this).val().indexOf('.') != -1) && (e.which < 48 || e.which > 57)) {
            return false;
        }
    });
}

function sv_update_param(element) {
    parameter = "";
    field = "";
    parameter_value = "0";

    if(element.contentEditable == "true")
    {
        index = $(element).index();
        parameter_value = $(element).html();
    }
    else // checkbox, color
    {
        index = $(element).parent().index();
        if(element.type == "checkbox") parameter_value = element.checked? "1":"0";
        if(element.type == "color") parameter_value = element.value;
    }
    parameter = $("#scopeTable tbody>tr").children()[2].textContent;
    parameter_field = $("#scopeTable thead>tr").children()[index].textContent;

    $.getJSON('/scope-view/update',
    {
        param: parameter,
        field: parameter_field,
        value: parameter_value
    });
}

function sv_update_scope_data() {
    $.getJSON('/scope-view/chart', function(data) {
        scopeChart.data.datasets = data.data;
        scopeChart.data.labels = data.labels;
        scopeChart.update('none');
    });
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

    $('#chartExport').attr("href", "scope-view/export")

}

function sv_data_ready_check()
{
    $.getJSON('/scope-view/data-ready', function(data) {
        if(data.finish) {
            clearInterval(dataReadyRefreshInterval);
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
        if(data.ready) sv_update_scope_data();
    });
}

function initScopeForms(){
    $("#sampleControlForm").submit(function(e) {
        e.preventDefault(); // avoid to execute the actual submit of the form.
        var form = $(this);

        $.ajax({
            type: "POST",
            url: "scope-view/form-sample",
            data: form.serialize(),
            success: function(data)
            {
              if(data.trigger){
                  clearInterval(dataReadyRefreshInterval);
                  dataReadyRefreshInterval = setInterval(sv_data_ready_check, 200);
              }
              else {
                  clearInterval(dataReadyRefreshInterval);
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
            url: "scope-view/form-trigger",
            data: form.serialize(), // serializes the form's elements.
            success: function(data){
            }
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
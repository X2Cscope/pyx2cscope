let scopeCardEnabled = true;
scopeTable;

function initScopeSelect(){
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
        $.getJSON('/scope-view-add',
        {
            param: parameter
        },
        function(data) {
            $('#scopeSearch').val(null).trigger('change');
            scopeTable.ajax.reload();
        });
    });
}

function setScopeTableListeners(){
    // delete Row on button click
    $('#scopeTableBody').on('click', '.remove', function () {
        parameter = $(this).parent().siblings()[2].textContent;
        $.getJSON('/scope-view-remove',
        {
            param: parameter
        },
        function(data) {
            scopeTable.ajax.reload();
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

    $.getJSON('/scope-view-update',
    {
        param: parameter,
        field: parameter_field,
        value: parameter_value
    });
}

function update_scope_data() {
    $.getJSON('/scope-view-plot', function(data) {
        sv_updateChart();
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

function sv_updateChart() {
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

function initScopeForms(){
    $("#sampleControlForm").submit(function(e) {
        e.preventDefault(); // avoid to execute the actual submit of the form.
        var form = $(this);

        $.ajax({
            type: "POST",
            url: "scope-view-form-sample",
            data: form.serialize(), // serializes the form's elements.
            success: function(data)
            {
              alert(data.trigger); // show response from the php script.
            }
        });
    });

    sampleTriggerButtons = document.querySelectorAll('input[name="triggerAction"]');
    sampleTriggerButtons.forEach(button => {
        button.addEventListener('click', function() {
            $("#sampleControlForm").submit();
        });
    });

}

$(document).ready(function () {
    initScopeSelect();
    setScopeTableListeners();
    initScopeForms();

    scopeTable = $('#scopeTable').DataTable({
        ajax: '/scope-view-data',
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

    update_scope_data();
});
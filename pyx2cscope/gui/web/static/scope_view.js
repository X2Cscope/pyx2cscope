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
        sv_update_param(null, this);
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

function sv_update_param(cb, element) {
    parameter = "";
    parameter_field = "";
    parameter_value = "0";
    if(element != null) { // contenteditable
        parameter = $(element).siblings()[1].textContent;
        index = $(element).index()
        parameter_field = $("#scopeTable thead>tr").children()[index].textContent;
        parameter_value = $(element).html();
    }
    if(cb != null) { // checkbox
        parameter = $(cb).parent().siblings()[0].textContent;
        parameter_field = "trigger";
        parameter_value = cb.checked? "1":"0";
    }
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

$(document).ready(function () {
    initScopeSelect();
    setScopeTableListeners();

    scopeTable = $('#scopeTable').DataTable({
        ajax: '/scope-view-data',
        searching: false,
        paging: false,
        info: false,
        columns: [
            {data: 'trigger', render: wv_checkbox},
            {data: 'enable'},
            {data: 'variable'},
            {data: 'color', orderable: false},
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
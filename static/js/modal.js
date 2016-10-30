function getModal(identifier) {
    console.log(identifier.id);
    $.get( "/modal", { id: identifier.id } , function(data) {
        $( ".modal-container" ).append(data);
        $( ".modal-container" ).css('visibility', 'visible');
        console.log($('#check_judge').prop('checked'));
        if ($('#check_judge').prop('checked')){
            $('.modal-container .judge-button').css('visibility', 'visible');
        }
        else{
            $('.modal-container .judge-button').css('visibility', 'hidden');
        }
        $( ".modal-container" ).show();
    });
};

function delModal(identifier) {
    $( ".modal-container" ).hide();
    $( ".modal-container" ).empty();
}

// creates a query to the database with the relevancy
function score(pressed) {
    var docid = $('#modal-overall #doc_id')[0].value;
    var data = {'relevant': pressed.value,
                'query': $('#query_string')[0].value,
                'judge': $('#judge_input')[0].value,
                'docid': docid,
                };

    var request = $.post('/api/score', data, function (data) {
        $(pressed).css('background-color', '#00ee00');
        $('.judge-button').attr('disabled', 'true');
        $('#'+ docid).attr('onclick', '');
        }).fail(function () {
            $(pressed).css('background-color', '#ee0000');
            $(pressed).attr('disabled', 'true');
        })
};

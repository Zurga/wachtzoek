function getModal(identifier) {
    console.log(identifier.id);
    $.get( "/modal", { id: identifier.id } , function(data) {
        console.log(data);
        $( ".modal-container" ).append(data);
        $( ".modal-container" ).css('visibility', 'visible');
        $( ".modal-container" ).show();
    });
};

function delModal(identifier) {
    $( ".modal-container" ).hide();
    $( ".modal-container" ).empty();
}

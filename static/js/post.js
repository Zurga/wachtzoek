$(document).ready(function(){
    $(document).on('submit', 'form',function(){
       localStorage.setItem("query", $('#query_string').val());
       localStorage.setItem("title", $('#title_string').val());
       localStorage.setItem("from", $('#from_string').val());
       localStorage.setItem("to", $('#to_string').val());
    });
});


function changePage(page) {
	$('.current').fadeOut().removeClass('current');
	$('#p'+page).fadeIn().addClass('current');
}


$(document).ready(function () {
	$('#p1').show().addClass('current');
	var pages = $('.page').length;
	pages > 1 && $('.pagination').paginate({
		count: pages,
		start: 1,
		display: 7,
		border: true,
		border_color: '#fff',
		text_color: '#fff',
		background_color: 'black',	
		border_hover_color: '#ccc',
		text_hover_color: '#000',
		background_hover_color: '#fff',
		images: true,
		mouse: 'press',
		onChange: changePage
	});
});

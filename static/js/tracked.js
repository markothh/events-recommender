$(function() {
    function renderCard(event) {
        const matchedTags = (event.matched_tags || []).map(t => `<span class="badge bg-secondary me-1">${t}</span>`).join("");

        const card = $(`
        <div class="col-md-3">
            <div class="event-card"
                 style="
                    cursor:pointer;
                    width:100%;
                    height:260px;
                    background: ${event.image ? `url(${event.image}) center/cover no-repeat` : '#f0f0f0'};
                    color:white;
                    border-radius:8px;
                    position:relative;
                    overflow:hidden;
                    display:block;
                 ">
                <div class="event-title"
                     style="
                        position:absolute;
                        top:0;
                        left:0;
                        width:100%;
                        background: rgba(0,0,0,0.55);
                        padding:6px 10px;
                        font-weight:600;
                        font-size:0.95rem;
                        text-shadow:0 1px 2px black;
                     ">
                    ${event.title}
                </div>
                <div class="event-bottom"
                     style="
                        position:absolute;
                        bottom:0;
                        left:0;
                        width:100%;
                        background: rgba(0,0,0,0.55);
                        padding:6px 10px;
                        font-size:0.85rem;
                     ">
                    ${event.place ? `<div class="event-place" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"><i class="bi bi-geo-alt"></i> ${event.place}</div>` : ''}
                    <div class="matched-tags" style="margin-top:6px; display:none; font-size:0.9rem;">
                        ${matchedTags}
                    </div>
                    <div class="grade-buttons" style="margin-top:6px; display:none;">
                        <button type="button" class="btn btn-success btn-like btn-sm me-1">Понравилось :)</button>
                        <button type="button" class="btn btn-danger btn-dislike btn-sm">Не понравилось :(</button>
                    </div>
                </div>
            </div>
        </div>`);

        card.find(".event-card").hover(
            function() {
                $(this).find(".matched-tags, .grade-buttons").slideDown(100);
            },
            function() {
                $(this).find(".matched-tags, .grade-buttons").slideUp(100);
            }
        );

        card.find(".btn-like, .btn-dislike").click(function(e){
            e.preventDefault();      // <-- Отключаем поведение кнопки по умолчанию
            e.stopPropagation();     // <-- Отключаем всплытие
            const liked = $(this).hasClass("btn-like");
            $.ajax({
                url: `/api/tracked-events/${event.id}/grade`,
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify({liked}),
                success: function(){
                    card.fadeOut(200, ()=> card.remove());
                },
                error: function(){
                    alert("Ошибка при оценке события");
                }
            });
        });

        card.find(".event-card").click(function(){
            window.location.href = `/event/${event.id}`;
        });

        return card;
    }

    function loadTracked() {
        $.getJSON("/api/tracked-events").done(function(data){
            $("#actual-cards").empty();
            $("#archive-cards").empty();

            data.actual.forEach(ev => {
                $("#actual-cards").append(renderCard(ev));
            });
            data.archive.forEach(ev => {
                $("#archive-cards").append(renderCard(ev));
            });
        });
    }

    loadTracked();
});

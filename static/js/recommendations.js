// static/js/recommendations.js
$(function(){
  const recsRoot = $("#recs");

  function renderEvents(events){
    recsRoot.empty();
    if (!events || events.length===0){
      recsRoot.html("<div class='text-muted'>Нет рекомендаций. Вы можете <a href='/select-interests'>выбрать интересы</a>.</div>");
      return;
    }
    events.forEach(e=>{
      const card = $(`
        <div class="event-tile d-flex justify-content-between align-items-start">
          <div>
            <a href="/event/${e.id}"><h5>${e.title}</h5></a>
            <div class="text-muted">${e.start_ts || ''} ${e.address ? (' — ' + e.address) : ''}</div>
            <div class="mt-2"><small>score: ${Math.round((e.score||0)*100)/100}</small></div>
          </div>
          <div class="text-end">
            <button class="btn btn-sm btn-outline-primary track" data-id="${e.id}">Отслеживать</button>
          </div>
        </div>`);
      recsRoot.append(card);
    });
    $(".track").click(function(){
      const id = $(this).data("id");
      $.ajax({url:"/api/track", method:"POST", contentType:"application/json", data: JSON.stringify({event_id:id, status:'upcoming'})})
        .done(()=> alert("Добавлено в отслеживаемое"));
    });
  }

  function fetchRecs(pos){
    $.ajax({
      url: "/api/recommendations",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(pos)
    }).done(function(data){
      renderEvents(data);
    }).fail(function(){
      recsRoot.html("<div class='text-danger'>Ошибка получения рекомендаций</div>");
    });
  }

  // Получаем геолокацию
  function obtainLocationAndFetch(){
    if (!navigator.geolocation){
      fetchRecs({lat:null, lon:null});
      return;
    }
    navigator.geolocation.getCurrentPosition(function(p){
      fetchRecs({lat: p.coords.latitude, lon: p.coords.longitude});
    }, function(err){
      // отказ — передаём null чтобы геоскор не учитывался
      fetchRecs({lat:null, lon:null});
    }, {timeout:5000});
  }

  $("#btn-refresh-recs").click(obtainLocationAndFetch);
  $("#btn-search").click(function(){
    const q = $("#search").val().toLowerCase();
    // для простоты: перезапрос рекомендаций и фильтр на клиенте
    obtainLocationAndFetch();
    // можно добавить client-side фильтр позже
  });

  obtainLocationAndFetch();
});

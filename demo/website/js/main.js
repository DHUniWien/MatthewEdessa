// define constants
var NEO4J_SERVER = "http://storage.stemmaweb.net:7474";
var CYPHER_URL = NEO4J_SERVER + "/db/data/cypher";
var SELF_URL = NEO4J_SERVER + "/db/data/node/";

var CONTENT_TYPE = "application/json; charset=UTF-8";
var BEFORE_SEND = function(xhr) {xhr.setRequestHeader("Authorization", "Basic bmVvNGo6Y3lLLUplay1WYQ==");};
var available_sections = [418, 485, 493, 500];
var current_section = undefined;
var section_cache = [];
var use_cache = true;

for (i in available_sections) {
	section_cache[available_sections[i]] = {title: undefined, reading: undefined, translation: undefined, readings: [], reading_ids: [], min_reading_id: undefined, max_reading_id: undefined, name_ids: []}
}

// functions

var warm_up_cache = function() {

	var person_info = [];

	// cache names' sections
	jQuery.ajax({
		async: false,
		type: "POST",
		url: CYPHER_URL,
		contentType: CONTENT_TYPE,
		dataType: "json",
		data: JSON.stringify({query: 'MATCH (bn:READING)<-[:BEGIN]-(pref:PERSONREF)-[:REFERS_TO]->(p:PERSON) RETURN id(p), id(pref), id(bn);', params: {}}),
		beforeSend: BEFORE_SEND,

		success: function(result,status,xhr) {
			// get each translation and print it
			for (i in result.data) {
				if (result.data[i] != undefined) {
					person_info.push({person_id: result.data[i][0], reading_id: result.data[i][2]});
				}
			}
		},
		error: function (xhr, status, error) {
			// an error occurred!
			var a = 0;
		}
	});


	for (i in available_sections) {
		section = available_sections[i]
		c_slot = section_cache[section];
		first_reading = undefined;
		last_reading = undefined;
		query_data = {query: "MATCH (first_reading)<-[:LEMMA_TEXT]-(start)<-[:COLLATION]-(n)-[:HAS_END]->(end)<-[:LEMMA_TEXT]-(last_reading) WHERE n:SECTION and n.name =~ '" + section + ".*' RETURN n.name, id(first_reading), id(end);", pararms: {}};

		// get title and first- and last reading ids
		jQuery.ajax({
			async: false,
			type: "POST",
			url: CYPHER_URL,
			contentType: CONTENT_TYPE,
			dataType: "json",
			data: JSON.stringify(query_data),
			beforeSend: BEFORE_SEND,

			success: function(result, status, xhr) {
				c_slot.title = result.data[0][0];
				c_slot.first_reading = result.data[0][1];
				c_slot.last_reading = result.data[0][2];
			},
			error: function(xhr,status,error) {
				// an error occurred!
				var a = 0;
			}
		});

		// get section's readings and reading ids
		request_data = {};
		request_data['order'] = 'depth_first';
		request_data['return_filter'] = {name: "all", language: "builtin"};
		request_data['prune_evaluator'] = {body: "position.endNode().getId() == " + c_slot.last_reading, language: "javascript"};
		request_data['uniqueness'] = 'node_global';
		request_data['relationships'] = {type: "LEMMA_TEXT", direction: "out"};

		jQuery.ajax({
			async: false,
			type: "POST",
			url: SELF_URL + c_slot.first_reading + "/traverse/node",
			contentType: CONTENT_TYPE,
			dataType: "json",
			data: JSON.stringify(request_data),
			beforeSend: BEFORE_SEND,

			success: function (result, status, xhr) {
				reading_ids = [];
				if (result != undefined) {
					for (i in result) {
						reading_ids.push(result[i].metadata['id']);
					}
				}
				min_reading_id = Math.min.apply(null, reading_ids);
				max_reading_id = Math.max.apply(null, reading_ids);

				for (p in person_info) {
					reading_id = person_info[p].reading_id;
					person_id = person_info[p].person_id;
					if ((reading_id >= min_reading_id) && (reading_id <= max_reading_id)) {
						if ((-1 == $.inArray(person_id, c_slot.name_ids)) && (0 <= $.inArray(reading_id, reading_ids))) {
							c_slot.name_ids.push(person_id);
						}
					}
				}
			},
			error: function(xhr,status,error) {
				// an error occurred!
				var a = 0;
			}
		});

		/*
										person_id = result.data[i][0];
					reading_id = result.data[i][2];
					for (s in available_sections) {
						c_slot = section_cache[available_sections[s]];
						if ((reading_id >= c_slot.min_reading_id) && (reading_id <= c_slot.max_reading_id)) {
							if ((-1 == $.inArray(person_id, c_slot.name_ids)) && (0 <= $.inArray(reading_id, c_slot.reading_ids))) {
								c_slot.name_ids.push(person_id);
							}
							break;
						}
					}
		*/
	}
}

var _name_refs = function(reading_ids) {
	query_data = JSON.stringify({query: 'MATCH (bn:READING)<-[:BEGIN]-(ref:PERSONREF)-[:END]->(en:READING), (ref)-[:REFERS_TO]->(p:PERSON) WHERE id(bn) IN {reading_ids} AND id(en) IN {reading_ids} RETURN id(bn), id(en), id(ref), id(p), p;', params: {reading_ids: reading_ids}});
	return _refs(query_data, 'n')
}

var _place_refs = function(reading_ids) {
	query_data = JSON.stringify({query: 'MATCH (bp:READING)<-[:BEGIN]-(ref:PLACEREF)-[:END]->(ep:READING), (ref)-[:REFERS_TO]->(p:PLACE) WHERE id(bp) IN {reading_ids} AND id(ep) IN {reading_ids} RETURN id(bp), id(ep), id(ref), id(p), p;', params: {reading_ids: reading_ids}});
	return _refs(query_data, 'p');
}

var _date_refs = function(reading_ids) {
	query_data = JSON.stringify({query: 'MATCH (bd:READING)<-[:BEGIN]-(ref:DATEREF)-[:END]->(ed:READING), (ref)-[:REFERS_TO]->(d:DATE) WHERE id(bd) IN {reading_ids} AND id(ed) IN {reading_ids} RETURN id(bd), id(ed), id(ref), id(d), d;', params: {reading_ids: reading_ids}});
	return _refs(query_data, 'd');
}

var _refs = function(query, type) {
	var result_data = [];
	jQuery.ajax({
		async: false,
		type: "POST",
		url: CYPHER_URL,
		contentType: CONTENT_TYPE,
		dataType: "json",
		data: query,
		beforeSend: BEFORE_SEND,

		success: function(result,status,xhr) {
			// get each translation and print it
			for (i in result.data) {
				if (result.data[i] != undefined) {
					result_data[result.data[i][0]] = {end_node: result.data[i][1], ref_id: result.data[i][2], obj_id: result.data[i][3], data: result.data[i][4].data, type: type};
				}
			}
		},
		error: function (xhr, status, error) {
			// an error occurred!
			var a = 0;
		}
	});
	return result_data;
}

var _get_translation = function(first_reading_id) {
	var ret_value = undefined;
	query_data = {query: 'match (tb)<-[:TRANS_BEGIN]-(t)-[:TRANS_END]->(te)-[:LEMMA_TEXT]->(nr) WHERE id(tb)={first_reading_id} return t.text, id(te), id(nr);', params: {first_reading_id: first_reading_id}};
		jQuery.ajax({
			async: false,
			type: "POST",
			url: CYPHER_URL,
			contentType: CONTENT_TYPE,
			dataType: "json",
			data: JSON.stringify(query_data),
			beforeSend: BEFORE_SEND,

			success: function(result,status,xhr) {
				// get each translation and print it
				for (i in result.data) {
					ret_value = {text: result.data[i][0], end_node: result.data[i][1], next_node: result.data[i][2]}
				}
			},
			error: function (xhr, status, error) {
				// an error occurred!
				var a = 0;
			}
		});

		return ret_value;
}

var _get_content = function(start_node_id, end_node_id) {
	var c_slot = section_cache[current_section];

	if (section_cache[current_section].reading == undefined && section_cache[current_section].translation == undefined) {
	// get all (reading)nodes between start_node and end_node
		request_data = {};
		request_data['order'] = 'depth_first';
		request_data['return_filter'] = {name: "all", language: "builtin"};
		request_data['prune_evaluator'] = {body: "position.endNode().getId() == " + end_node_id, language: "javascript"};
		request_data['uniqueness'] = 'node_global';
		request_data['relationships'] = {type: "LEMMA_TEXT", direction: "out"};

		sub_request_json_data = 
		jQuery.ajax({
			async: false,
			type: "POST",
			url: SELF_URL + start_node_id + "/traverse/node",
			contentType: CONTENT_TYPE,
			dataType: "json",
			data: JSON.stringify(request_data),
			beforeSend: BEFORE_SEND,

			success: function (result, status, xhr) {
				var _get_reading_ids = function(nodes) {
					ret_value = [];
					if (nodes != undefined) {
						for (i in nodes) {
							ret_value.push(nodes[i].metadata['id']);
						}
					}
					return ret_value;
				}
				// print the 'text'-property for each node in '#reading'
				var reading_ids = _get_reading_ids(result);
				var name_refs = _name_refs(reading_ids);
				var place_refs = _place_refs(reading_ids);
				var date_refs = _date_refs(reading_ids);
				var reading = "";
				var translation = "";
				var i = 0;
				var stack = [];
				var dd_info = "";
				var map_ids = [];
				var place_ids = [];
				var name_sections = [];
				person_id = undefined;
				for (sc in available_sections) {
					name_sections[available_sections[sc]] = [];
				}
				while (i < result.length){
					reading_id = result[i].metadata['id'];
					translation_data = _get_translation(reading_id);
					if (translation_data != undefined) {
						translation += translation_data['text'] + ' ';
						while(reading_id != translation_data['next_node']) {
							node_text = result[i].data['text']; // with node
							if (node_text != "") {
								if (reading != "") {
									reading += " ";
								}
								if (name_refs[reading_id] != undefined) {
									data = name_refs[reading_id].data;
									dd_ref_id = "dd_" + name_refs[reading_id].ref_id;
									if (data.id != undefined && data.id.length > 0) {
										dd_content = '<li><a>'+data.id+'</a></li>';
									}
									if (data.description != undefined && data.description.length > 0) {
										dd_content += ('<li><a>('+data.description+')</a></li>');
									}
									other_sections = ""
									for (sc in section_cache) {
										if (sc != current_section) {
											if (0 <= $.inArray(name_refs[reading_id].obj_id, section_cache[sc].name_ids)) {
												other_sections += " <span id='" + name_refs[reading_id].ref_id +"'>" + sc + " <i class='fa fa-link'></i></span>";
												name_sections[sc].push(name_refs[reading_id].ref_id);
											}
										}
									}
									if (other_sections.length > 0) {
										dd_content += "<li><a>Also in section:" + other_sections + "</a></li>"
									}
									external_links = "";
									if (data.pbw != undefined && data.pbw.length > 0) {
										external_links = "<li><a href='"+data.pbw+"' target='_'>PBW <i class='fa fa-external-link'></i></a></li>";
									}
									if (data.wikipedia != undefined && data.wikipedia.length > 0) {
										external_links += "<li><a href='"+data.wikipedia+"' target='_'>Wikipedia <i class='fa fa-external-link'></i></a></li>";
									}
									if (external_links.length > 0) {
										dd_content += ("<hr/>"+external_links);
									}
									if (dd_content.length > 0) {
										dd_info += '<ul id="'+dd_ref_id+'" class="small f-dropdown" data-dropdown-content><li>'+dd_content+'</li></ul>';
									}
									node_text = '<span class="person" data-dropdown="'+dd_ref_id+'" data-options="is_hover:true; align:top; hover_timeout:500">' + node_text; // + dd_content;
									stack.push({id: name_refs[reading_id].end_node, closing_tag:'</span>'});
								}
								if (place_refs[reading_id] != undefined) {
									dd_content = "";
									dd_ref_id = 'dd_'+place_refs[reading_id].ref_id;
									place_id = place_refs[reading_id].data.id;
									place_name = place_refs[reading_id].data.canonical_name;
									place_place = place_refs[reading_id].data.place_id;

									if (place_id != undefined && place_id.length > 0) {
										dd_content = '<li><a>'+place_id+'</a></li>';
									}
									if (place_name != undefined && place_name.length > 0) {
										dd_content += '<li><a>'+place_name+'</a></li>';
									}
									if (place_place != undefined && place_place.length > 0) {
										dd_map_id = 'dd_map_'+place_refs[reading_id].ref_id;
										dd_content += '<li><a><div id="'+dd_map_id+'" style="width:none; height:350px; border: 2px solid #3872ac;"></div></a></li>';
										map_ids.push({id: dd_ref_id, map_id: dd_map_id, place_id: place_place});
										if (-1 == $.inArray(place_place, place_ids)) {
											place_ids.push(place_place);
										}
									}
									dd_info += '<ul id="'+dd_ref_id+'" class="small f-dropdown" data-dropdown-content><li>'+dd_content+'</li></ul>';
									node_text = '<span class="place" data-dropdown="'+dd_ref_id+'" data-options="is_hover:true; align:top; hover_timeout:500">' + node_text;
									stack.push({id: place_refs[reading_id].end_node, closing_tag: '</span>'});
								}
								if (date_refs[reading_id] != undefined) {
									dd_content = '<a>'+date_refs[reading_id].data.id+'</a>';
									dd_ref_id = 'dd_'+date_refs[reading_id].ref_id;
									dd_info += '<ul id="'+dd_ref_id+'" class="small f-dropdown" data-dropdown-content><li>'+dd_content+'</li></ul>';
									node_text = '<span class="date" data-dropdown="'+dd_ref_id+'" data-options="is_hover:true; align:top; hover_timeout:500">' + node_text;
									stack.push({id: date_refs[reading_id].end_node, closing_tag: '</span>'})
								}
								while(stack.length > 0 && stack[stack.length-1]['id'] == reading_id) {
									data = stack.pop();
									node_text += data.closing_tag;
								}

								reading += node_text;
							}
							i += 1;
							reading_id = result[i].metadata['id'];
						}
					} else {
						i += 1;
					}
				}

				// store results in cache
				c_slot.reading = reading + ' '+dd_info;
				c_slot.translation = translation;
				c_slot.map_ids = map_ids;
				c_slot.gmap_places = place_ids;
				c_slot.name_sections = name_sections;
			},
			error: function (xhr, status, error) {
			 	// an error occurred!
				var a = 0;
			}
		});
	}

	c_slot = section_cache[current_section];
	// display reading and translation
	$('#reading').append(c_slot.reading);
	$('#translation').append(c_slot.translation);

	// initialize persons' jumps to other sections
	for (sc in c_slot.name_sections) {
		for (link in c_slot.name_sections[sc]) {
			$('#'+ c_slot.name_sections[sc][link]).on('click', {section: sc}, function(ev) {
				display_content(ev.data.section);
				return false;
			});
		}
	}

	// initialize maps inside text
	for (i in c_slot.map_ids) {
		data = c_slot.map_ids[i];
		$('#'+data.id).on('opened.fndtn.dropdown', {map_id: data.map_id, place_ids: data.place_id}, function(ev) {
			var data = ev.data;
			initialize_map(data.map_id, [data.place_ids], 10);
		});
	}

	// initialize general map at the bottom
	if (c_slot.gmap_places.length>0) {
		$('#general_map').append('<br/><h3>Locations mentioned in this section:</h3><div id="g_map" style="width:none; height:350px; border: 2px solid #3872ac;"></div><br/>');
		initialize_map('g_map', c_slot.gmap_places, 5);
	}
}

var clear_content = function() {
	$('#headline').empty();
	$('#reading').empty();
	$('#translation').empty();
	$('#general_map').empty();
}

var display_content = function(section_nr) {

	if (current_section != section_nr) {
		current_section = section_nr;

		clear_content();

		if (use_cache == true) {
			c_slot = section_cache[current_section];
			$('#headline').append("<h1>"+c_slot.title+"</h1>");
			_get_content(c_slot.first_reading, c_slot.last_reading);
			$(document).foundation('dropdown', 'reflow');					
		} else {
			query_data = {query: "MATCH (first_reading)<-[:LEMMA_TEXT]-(start)<-[:COLLATION]-(n)-[:HAS_END]->(end)<-[:LEMMA_TEXT]-(last_reading) WHERE n:SECTION and n.name =~ '" + section_nr + ".*' RETURN n.name, id(first_reading), id(end);", pararms: {}};

			jQuery.ajax({
				type: "POST",
				url: CYPHER_URL,
				contentType: CONTENT_TYPE,
				dataType: "json",
				data: JSON.stringify(query_data),
				beforeSend: BEFORE_SEND,

				success: function(result, status, xhr) {
					$('#headline').append("<h1>"+result.data[0][0]+"</h1>");
					_get_content(result.data[0][1], result.data[0][2]);    // (first_reading, last_reading)
					$(document).foundation('dropdown', 'reflow');
				},
				error: function(xhr,status,error) {
					// an error occurred!
					var a = 0;
				}
			});
		}
	}
}

function initialize_map(map_canvas_id, place_ids, zoom) {
    var map = new google.maps.Map(
    document.getElementById(map_canvas_id), {
        center: new google.maps.LatLng(0, -0),
        zoom: zoom,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });
    var request = {
        placeId: place_id
    };

	var infowindow = new google.maps.InfoWindow();
	var service = new google.maps.places.PlacesService(map);

	var counter = 0;
	for (i in place_ids) {
		var request = {
	    	placeId: place_ids[i]
		};
		service.getDetails(request, function(place, status) {
			if (status == google.maps.places.PlacesServiceStatus.OK) {
				var marker = new google.maps.Marker({
					map: map,
					position: place.geometry.location
				});
				google.maps.event.addListener(marker, 'click', function() {
				infowindow.setContent(place.name);
				infowindow.open(map, this);
				});
				if (place.geometry.viewport) {
					map.fitBounds(place.geometry.viewport);
				} else {
					map.setCenter(place.geometry.location);
				}
				map.setZoom(zoom);
			}
		});
	}
}

var updateInterval = 100;


async function post_data(json_data) {
    // sends JSON data to python in the form of a POST request
    let response = await fetch(document.location.href, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(json_data),
    });
    let data = await response.json();
    return data;
}

async function get_data(url) {
    // receive data from python through a GET request
    let response = await fetch(url);
    let data = await response.json();
    return data;
}

function handle_onclick(event) {
    let data = {"topic": "onclick", "id": -1, "payload": {"id": event.target.id}};
    post_data(data);
}

function post_response(input_json, data) {
    post_data({"topic": input_json["topic"], "id": input_json["id"], "payload": data});
}

function on_page_load() {
    let buttons = document.querySelectorAll("input[type=button]");
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].setAttribute("onclick", "handle_onclick(event);")
    }

    var handle_event_loop = function () {
        let promise = post_data({"topic": "command_loop", "id": -1, "payload": null});
        promise.then((input_json) => {
            var response;

            switch (input_json["topic"]) {
                case "javascript":
                    response = eval(input_json["payload"]);
                    break;
                case "update_interval":
                    updateInterval = input_json["payload"];
                    break;
                default:
                    break;
            }

            if (input_json["should_respond"]) {
                post_response(input_json, (response === undefined) ? null : response);
            }
        });
        setTimeout(handle_event_loop, updateInterval);
    }

    setTimeout(handle_event_loop, updateInterval);
}

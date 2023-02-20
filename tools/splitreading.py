import json
import requests
import utils

# Make the request to split the reading
def split_reading(session, options, apibase):
    """Make the request to split the reading"""
    BASEURL = "%s/%s" % (apibase, options.tradition_id)
    headers = {'Content-Type': 'application/json'}
    spec = {'character': options.character, 
            'separate': options.separate, 
            'isRegex': options.isRegex}
    r = session.post(BASEURL + "/reading/%d/split/%d" 
                        % (options.reading, options.index), 
                      headers=headers, 
                      data=json.dumps(spec))
    if r.status_code > 399:
        print(r.text)
    else:
        print(r.json())


if __name__ == '__main__':
    parser = utils.arg_parser()
    ops = parser.add_argument_group('Reading split operation')
    ops.add_argument(
        "-r",
        "--reading",
        type=int,
        help="ID of reading to split"
    )
    ops.add_argument(
        "-i",
        "--index",
        type=int,
        default=0,
        help="Index of the character where the reading should be split"
    )
    ops.add_argument(
        "-c",
        "--character",
        default=" ",
        help="Character to split on (default: space)"
    )
    ops.add_argument(
        "-s",
        "--separate",
        action="store_true",
        help="Specify this if the readings should be space separated"
    )
    ops.add_argument(
        "-rx",
        "--isRegex",
        action="store_true",
        help="Specify this if "
    )

    args = parser.parse_args()

    # Log in to Stemmaweb
    s = requests.Session()
    apibase = utils.stemmaweb_login(args.username, args.password, s)
    split_reading(s, args, apibase)


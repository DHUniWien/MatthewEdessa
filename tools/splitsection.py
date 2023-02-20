import requests
import utils

# Make the request to split the reading
def split_section(session, options, apibase):
    """Make the request to split the section"""
    BASEURL = "%s/%s" % (apibase, options.tradition_id)

    # Were we called with a reading?
    if args.reading:
        r = session.get(BASEURL + "/reading/%d" % options.reading)
        r.raise_for_status
        rdg = r.json()
        splitRank = rdg.get('rank')
    else:
        splitRank = options.rank

    # headers = {'Content-Type': 'application/json'}
    r = session.post(BASEURL + "/section/%d/splitAtRank/%d" 
                        % (options.section_id, splitRank), 
                      )
    if r.status_code > 399:
        print(r.text)
    else:
        print(r.json())


if __name__ == '__main__':
    parser = utils.arg_parser()
    ops = parser.add_mutually_exclusive_group(required=True)
    ops.add_argument(
        "-rdg",
        "--reading",
        type=int,
        help="ID of reading where the section should be split"
    )
    ops.add_argument(
        "-rk",
        "--rank",
        type=int,
        help="Rank where the section should be split"
    )

    args = parser.parse_args()

    # Log in to Stemmaweb
    s = requests.Session()
    apibase = utils.stemmaweb_login(args.username, args.password, s)
    split_section(s, args, apibase)


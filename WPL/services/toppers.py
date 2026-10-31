"""The stats leaderboards: refreshing them from the feed, and reading them back.

Same table and same shape as the IPL app - one Toppers row per leaderboard,
holding a list of rows under keys like StrikerName / TeamCode / TotalRuns - but
the source underneath is not the same, and that is what this module is for.

The IPL publishes a feed of named fields. Cricbuzz, which is where the WPL
numbers come from, publishes a header row and bare positional values, with its
own spellings ("Mat", "4s", "BBI") and its own idea of which columns a given
leaderboard carries. Folding one into the other here - rather than teaching the
pages two vocabularies - is what lets the home-page toppers carousel, the
batting and bowling leaderboards and the awards page stay as they are.

The header -> field map lives in config.json under stats_map, because header
spellings are the part most likely to drift. A header nothing matches is kept
under its own name rather than dropped, so a column cricbuzz adds mid-season
shows up as itself instead of disappearing.
"""
import json
import re
from sqlalchemy.sql import text
from sqlalchemy.orm.attributes import flag_modified
from collections import Counter

from .. import db
from ..models import Squad, Toppers
from ..config import statsList, statsMap, full_name, full_name2, SEASON_YEAR
from ..utils.formatting import serialize
from .players import find_player
from .player_stats import get_player_stats
from .feeds import get_stats_feed

# Team long name -> our abbreviation, for the "Vs" column. Both spellings are
# accepted because cricbuzz is not consistent about the Women suffix between
# leaderboards.
_ABV_OF = {}
for _map in (full_name2, full_name):
    for _abv, _name in _map.items():
        _ABV_OF.setdefault(_name, _abv)

_KEY_RE = re.compile(r'[^a-z0-9/]+')


def _header_key(header):
    """A header as stats_map keys it: lowercased, punctuation and spaces gone.

    "N/O" keeps its slash because that is how the map spells it; everything
    else collapses, so "Best Bowling", "best-bowling" and "BestBowling" are one
    key.
    """
    return _KEY_RE.sub('', str(header or '').strip().lower())


def _normalise(headers, rows, group, squad):
    """Cricbuzz's header row + value rows -> rows in the IPL feed's shape.

    The player column is whichever one the map names as the player, and it is
    also what the team is resolved from: cricbuzz gives a name and no team, so
    find_player() against the Squad table supplies both our spelling of the name
    and the crest the row should wear. A name that cannot be resolved keeps
    cricbuzz's spelling and reads as "NA" for the team, which is a far smaller
    error than pinning a leaderboard place on the wrong player.
    """
    spec = statsMap.get(group) or {}
    fields = spec.get('fields') or {}
    player_key = spec.get('player') or 'PlayerName'
    team_key = spec.get('team') or 'TeamCode'

    names = []
    for head in headers:
        key = _header_key(head)
        names.append(fields.get(key, str(head or '').strip()))

    out = []
    for values in rows:
        row = {}
        for name, value in zip(names, values):
            row[name] = value
        if player_key in row:
            player = find_player(row[player_key], squad)
            row[player_key] = player[2] if player is not None else row[player_key]
            row[team_key] = player[3] if player is not None else 'NA'
        # "Vs" arrives as the opposition's full name; everything downstream
        # draws a crest from it, so it has to be an abbreviation.
        against = row.get('AgaintsTeamCode')
        if against:
            row['AgaintsTeamCode'] = _ABV_OF.get(str(against).strip(), against)
        out.append(row)
    return out


def update_potm():
    """Most player-of-the-match awards, counted off the fixtures.

    Nothing publishes this, so it is built here from the POTM stored on each
    result and then enriched from the player's own season record - which is
    what the ties are broken on when two players are level on awards.
    """
    potms = (db.session.execute(text('SELECT "POTM" FROM Fixture WHERE "POTM" IS NOT NULL')).fetchall())
    counts = Counter([(p[0]['name'], p[0]['team']) for p in potms])
    potms = [{"name": name, "team": team, "potm": count} for (name, team), count in counts.items()]

    for potm in potms:
        sq = Squad.query.filter_by(Name=potm['name']).first()
        stats = get_player_stats(sq.Player_URL) if sq else None
        season = (stats or {}).get(SEASON_YEAR)
        if season:
            bat, bowl = season.get('batting') or {}, season.get('bowling') or {}
            potm['matches'] = int(bat['Matches']) if bat.get('Matches') else 0
            potm['innings'] = int(bat['Innings']) if bat.get('Innings') else 0
            potm['runs'] = int(bat['Runs']) if bat.get('Runs') else 0
            potm['wickets'] = int(bowl['Wickets']) if bowl.get('Wickets') else 0

    try:
        potms = sorted(potms, key=lambda x: (x['potm'], x['runs'], x['wickets']), reverse=True)
    except Exception as e:
        print(f"Error while sorting the toppers for Most POTM: {e}")
    finally:
        potms = sorted(potms, key=lambda x: (x['potm']), reverse=True)
        toppers = Toppers.query.filter_by(category="Most POTM").first()
        if toppers:
            toppers.stats = potms
            db.session.commit()


def update_toppers():
    """Refresh every leaderboard from the feed, into the Toppers table.

    A leaderboard the feed cannot answer for keeps whatever it already had,
    with the player names re-resolved against the squad in case the squad has
    moved on - the same failure path the IPL app takes. A leaderboard the feed
    answers for with nothing is cleared, because that is a real answer.
    """
    SquadFull = (db.session.execute(text('SELECT * FROM Squad')).fetchall())
    update_potm()
    for stats_type, stats in statsList.items():
        for stat_name, token in stats.items():
            tp = Toppers.query.filter_by(category=stat_name).first()
            if tp is None:
                continue
            try:
                headers, rows = get_stats_feed(token)
                if headers is None:
                    raise RuntimeError('feed unavailable')
                tp.stats = _normalise(headers, rows, stats_type, SquadFull) if rows else None
                db.session.commit()
            except Exception as e:
                print(f"Error updating toppers for {stat_name}: {e}")
                print(f"Mapping Player Name for existing for {stat_name} if any (Failure case)")
                if tp.stats:
                    player_key = (statsMap.get(stats_type) or {}).get('player')
                    team_key = (statsMap.get(stats_type) or {}).get('team') or 'TeamCode'
                    for row in tp.stats:
                        player_name = row.get(player_key) if player_key else None
                        if not player_name:
                            continue
                        player = find_player(player_name, SquadFull, team=row.get(team_key))
                        if player:
                            row[player_key] = player[2]
                            row[team_key] = player[3]

                    flag_modified(tp, "stats")
                    db.session.commit()


def get_stats():
    """Every leaderboard, keyed by category, for /api/stats.

    The rows come back from a raw text() SELECT, so SQLAlchemy does not know
    the stats column is JSON: Postgres hands a list back either way, SQLite
    hands back the text it stored. Decoding here means the page always
    receives a list of rows rather than, on SQLite, one long string.
    """
    tp = db.session.execute(text('SELECT category, stats FROM Toppers ORDER BY id ASC')).fetchall()
    out = {}
    for category, stats in tp:
        if isinstance(stats, str):
            try:
                stats = json.loads(stats)
            except ValueError:
                stats = None
        out[category] = stats
    return serialize({'stats': out})

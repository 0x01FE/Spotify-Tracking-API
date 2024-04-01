-- Top Artists
SELECT
    artist_name,
    sum(time),
    spotify_id
FROM
    (SELECT
        artists.name artist_name,
		artists.id artist_id,
        songs.name song_name,
        SUM("listen-events".time) time,
        artists.spotify_id spotify_id
    FROM
        "listen-events"
    INNER JOIN songs ON "listen-events".song=songs.id
    INNER JOIN artists ON songs.artist=artists.id
    WHERE
        "listen-events".user = ?
    GROUP BY
        "listen-events".song,
        songs.artist)
GROUP BY
    artist_name
ORDER BY
    SUM(time) DESC
LIMIT ?;

-- Top Artists with date range
SELECT
    artist_name,
	artist_id,
    sum(time)
FROM
    (SELECT
        artists.name artist_name,
		artists.id artist_id,
        songs.name song_name,
        SUM("listen-events".time) time
    FROM
        "listen-events"
    INNER JOIN songs ON "listen-events".song=songs.id
    INNER JOIN artists ON songs.artist=artists.id
    WHERE
        "listen-events".user = ?
        AND DATE("listen-events".date) BETWEEN ? AND ?
    GROUP BY
        "listen-events".song,
        songs.artist)
GROUP BY
    artist_name
ORDER BY
    SUM(time) DESC;

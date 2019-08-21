# Sharepoint list reader

This microservice reads a sharepoint list and returns it's entries a stream of JSON entities.

## Environment variables
`base_url` (required) - url path to the sharepoint site

`password` (required) - password to the sharepoint site

`user` (required) - user name to the sharepoint site

## URL variables
`since_path` (optional) - source property to set the native Sesam property `_updated`

## Example System Config
```
{
  "_id": "sharepoint-site",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "base_url": "http://some.base.url/path/to/sharepoint/site/_api/Web/",
      "password": "$SECRET(password)",
      "username": "$ENV(user)"
    },
    "image": "sesamcommunity/sharepoint-list:0.5",
    "port": 5000
  }
}
```

## Example Pipe configs
### ... to fetch from a native sharepoint list
```
{
  "_id": "bruker",
  "type": "pipe",
  "source": {
    "type": "json",
    "system": "sharepoint-site",
    "supports_since": true,
    "url": "SiteUserInfoList"
  }
}
```

### ... to fetch from a user defined sharepoint list using getByTitle()
```
{
  "_id": "oppgave",
  "type": "pipe",
  "source": {
    "type": "json",
    "system": "sharepoint-site",
    "supports_since": true,
    "url": "Lists/getByTitle('Oppgaver')?since_path=Modified"
  }
}
```

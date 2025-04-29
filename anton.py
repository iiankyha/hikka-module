async def anton(event):
    if not event.text.startswith(".anton"):
        return

    await event.message.edit("my def is @seys666228")

async def load(client):
    client.add_event_handler(anton)

async def unload(client):
    client.remove_event_handler(anton)

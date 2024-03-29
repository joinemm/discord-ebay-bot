from discord.ext import commands
import discord
from ebaysdk.finding import Connection
from data import db
from datetime import datetime
import os
import asyncio
import random


class Ebay(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.api = Connection(appid=os.environ.get('EBAY_APPID'), config_file=None)
        self.run = False
        self.posted_ids = {}
        self.start_time = datetime.now().timestamp()
        self.ignore_ts = False
        self.colors = [discord.Color.red(), discord.Color.blue(), discord.Color.gold(), discord.Color.green()]

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.run:
            self.run = True
            print("Starting event loop")
            await self.loop()

    async def loop(self):
        while self.run:
            keywords = db.get_keywords() or []
            #try:
            for query in keywords:
                query = query[0]
                #try:
                await self.check_for_new(query)
                #except Exception as e:
                    #print(f"Problem querying {query}:\n{e}")
            #except Exception as e:
                #print(e)

            sleeptime = 60 * len(db.get_keywords() or [1])
            print(f"sleeping for {sleeptime}s")
            await asyncio.sleep(sleeptime)

    def make_request(self, endpoint, parameters):
        response = self.api.execute(endpoint, parameters)
        return response

    async def check_for_new(self, query, channel_id=None):
        response = self.make_request('findItemsByKeywords', {'keywords': query, 'sortOrder': 'StartTimeNewest'})

        if int(response.reply.searchResult._count) == 0:
            # print(f"no results at all found for {query}")
            pass

        else:
            if channel_id is None:
                channel_id, is_dm = db.query("""SELECT channel_id, is_dm FROM keywords WHERE keyword = ?""",
                                             (query,))[0]
            else:
                is_dm = None

            new_items = []
            for item in response.reply.searchResult.item[:10]:
                if  item.listingInfo.startTime.timestamp() > self.start_time or self.ignore_ts:
                    if item.globalId not in self.posted_ids.get(str(channel_id), []):
                        new_items.append(item)
                    else:
                        # print(f"No more new in {query}")
                        break

            for item in reversed(new_items):
                if self.posted_ids.get(str(channel_id)) is None:
                    self.posted_ids[str(channel_id)] = set()
                self.posted_ids[str(channel_id)].add(item.globalId)
                await self.post_new_listing(channel_id, item, is_dm)

    async def post_new_listing(self, channel_id, item, is_dm=None):
        if is_dm:
            channel = self.client.get_user(channel_id)
        else:
            channel = self.client.get_channel(channel_id)
        if channel is None:
            print(f"could not find channel/user {channel_id}")
            return
        content = self.listing_to_embed(item)
        await channel.send(embed=content)
        print(f"#{channel.name} <<< {item.title}")

    def listing_to_embed(self, item):
        # print(item)
        content = discord.Embed(color=random.choice(self.colors))
        price = f"**{item.sellingStatus.currentPrice.value}** {item.sellingStatus.currentPrice._currencyId}"
        try:
            price_shipping = f"+ **{item.shippingInfo.shippingServiceCost.value}** " \
                             f"{item.shippingInfo.shippingServiceCost._currencyId} " \
                             f"{item.shippingInfo.shipToLocations} shipping" \
                if float(item.shippingInfo.shippingServiceCost.value) > 0 else ""
        except AttributeError as e:
            # print(e)
            price_shipping = f"{item.shippingInfo.shippingType}"
        content.set_author(name=item.title, url=item.viewItemURL)
        content.add_field(name="Price", value=f"{price} {price_shipping}")
        content.add_field(name="Listing type", value=f"{item.listingInfo.listingType}")
        content.add_field(name="Location", value=f"{item.globalId} | {item.location}")
        #content.add_field(name="Category", value=item.primaryCategory.categoryName)
        content.timestamp = item.listingInfo.startTime
        content.set_footer(text=item.itemId)
        content.set_image(url=item.galleryURL)
        return content

    @commands.command()
    async def check(self, ctx, *, keywords):
        await self.check_for_new(keywords, ctx.channel.id)

    @commands.command()
    async def get_newest(self, ctx, *, keywords):
        response = self.make_request('findItemsByKeywords', {'keywords': keywords, 'sortOrder': 'StartTimeNewest'})

        await self.post_new_listing(ctx.channel.id, response.reply.searchResult.item[0])

    @commands.command()
    async def add(self, ctx, _channel, *, keyword):
        dm = False
        if _channel.lower() == "dm":
            channel = ctx.author
            dm = True
        else:
            channel = await commands.TextChannelConverter().convert(ctx, _channel)
            if channel is None:
                return await ctx.send(f"Invalid channel {_channel}")

        db.add_keyword(ctx.guild.id, channel.id, keyword, dm)

        await ctx.send(f"Now updating new `{keyword}` listings in {channel.mention}" + ("DMs" if dm else ""))

    @commands.command()
    async def remove(self, ctx, _channel, *, keyword):
        if _channel.lower() == "dm":
            channel = ctx.author
        else:
            channel = await commands.TextChannelConverter().convert(ctx, _channel)
            if channel is None:
                return await ctx.send(f"Invalid channel {_channel}")

        db.remove_keyword(channel.id, keyword)

        await ctx.send(f"Removed `{keyword}` from {channel.mention}")

    @commands.command()
    async def search(self, ctx, *, keywords):
        response = self.make_request('findItemsByKeywords', {'keywords': keywords, 'sortOrder': 'StartTimeNewest'})

        if int(response.reply.searchResult._count) == 0:
            return await ctx.send("0 results.")

        content = discord.Embed()
        for item in response.reply.searchResult.item[:10]:
            price = f"{item.sellingStatus.currentPrice.value}{item.sellingStatus.currentPrice._currencyId}"
            content.add_field(name=item.title, value=f"{price}")
        await ctx.send(embed=content)

    @commands.command(name='list')
    async def list_follows(self, ctx):
        data = db.query("SELECT keyword, channel_id FROM keywords")
        content = discord.Embed(title="Followed keywords", color=discord.Color.red())
        content.description = ''
        for row in data:
            content.description += f"`{row[0]}` >>> <#{row[1]}>\n"
        await ctx.send(embed=content)


def setup(client):
    client.add_cog(Ebay(client))

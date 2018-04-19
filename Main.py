import discord
from discord.ext import commands
import asyncio
import os
import sys
from io import StringIO
from pickle import dump, load
import pickle

rawCommands = []
imports = dict()

def addimport(module):
    if module in imports: return imports[module]
    imports[module] = __import__(module)
    return imports[module]

def loadFromPickle(filename):
    try:
        with open(filename + ".pickle", 'rb') as f:
            return load(f)
    except Exception as e:
        try:
            if os.path.exists(filename + "_backup.pickle"):
                with open(filename + "_backup.pickle", 'rb') as f:
                    return load(f)
            else:
                print("Corrupted or missing command pickle file! Loading nothing.\nException: %s" % e)
        except Exception as e2:
            print("Corrupted command pickle file and backup! Loading nothing.\nException: %s\n%s" % (e, e2))
    

def setupRawCommands(bot):
    global rawCommands
    rawCommands = []
    
    bot.remove_command('exec')
    rawCommands.append('exec')
    rawCommands.append('debug')
    rawCommands.append('run')
    @bot.command(pass_context=True, name = 'exec', aliases = ['debug', 'run'])
    @developerCheck
    async def debug(ctx, *, arg):
        # https://stackoverflow.com/questions/3906232/python-get-the-print-output-in-an-exec-statement
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        bot = ctx.bot
        try:
            fix = lambda f: (lambda x: x(x))(lambda y: f(lambda args: y(y)(args)))
            bot.log.append(arg)
            exec(arg)
        except SystemExit:
            await bot.say("I tried to quit().")
        finally:
            sys.stdout = old_stdout
        output = redirected_output.getvalue()
        output = "No output." if not output else output
        bot.log.append(output)
        await bot.say(output)
        
    bot.remove_command('registerCommand')
    rawCommands.append('registerCommand')
    rawCommands.append('addCommand')
    @bot.command(pass_context=True, name='registerCommand', aliases = ['addCommand'])
    async def registerCommand(ctx, *, arg):
        bot.customCommands.append(arg)
        await bot.say("Command registered! I hope you tested it first.")
        
    bot.remove_command('removeCommand')
    rawCommands.append('removeCommand')
    @bot.command(pass_context=True, name='removeCommand')
    async def registerCommand(ctx, comm):
        if comm in rawCommands:
            await bot.say("I can't let you do that.")
        else:
            bot.remove_command(comm)
            await bot.say("Command removed.")
        
    bot.remove_command('save')
    rawCommands.append('save')
    @bot.command(pass_context=True, ignore_extra = False)
    async def save(ctx):
        bot = ctx.bot
        try:
            with open('commands.pickle', 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                dump((bot.customCommands, imports), f, pickle.HIGHEST_PROTOCOL)
            with open('commands_backup.pickle', 'wb') as f:
                dump((bot.customCommands, imports), f, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            await bot.say("Error saving commands.\nException: %s" % e)
            return
        await bot.say("Commands successfully saved.")

    bot.remove_command('saveLog')
    rawCommands.append('saveLog')
    @bot.command(pass_context=True, ignore_extra = False)
    async def saveLog(ctx):
        log = ctx.bot.log
        try:
            with open('log.txt', 'a+') as f:
                for entry in log:
                    f.write("%s\n\n" % entry)
            ctx.bot.log = []
            await ctx.bot.say("Log saved to file and cleared.")
        except Exception as e:
            await ctx.bot.say("Error saving log.\nException: %s" % str(e))
            
    bot.remove_command('clearLog')
    rawCommands.append('clearLog')
    @bot.command(pass_context=True, ignore_extra = False)
    async def clearLog(ctx):
        ctx.bot.log = []
        await ctx.bot.say("Log cleared.")

if __name__ == "__main__":
    bot = commands.Bot(command_prefix=['>', 'do '], description='Hotplugging.')

    developerIDs = ['91393737950777344']
    developerCheck = commands.check(lambda x: x.message.author.id in developerIDs)

    @bot.event
    async def on_ready():
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------')
        await bot.change_presence(game=discord.Game(name="Executing."))

    @bot.add_listener
    async def on_command_error(error, ctx):
        if type(error) == commands.CheckFailure:
            pass
        elif type(error) == commands.CommandNotFound:
            pass
        else:
            await bot.send_message(ctx.message.channel, error)

    token = os.environ.get('TOKEN', default=None)
    if token is None:
        token = open('./token').read().replace('\n','')

    # Load previously saved commands.
    res = loadFromPickle("commands")
    if type(res) is not tuple or type(res[0]) is not list:
        print("Loaded commands are not a list. Loading nothing.")
        bot.customCommands = []
    else:
        (bot.customCommands, imports) = res
        for comm in bot.customCommands:
            try:
                exec(comm)
            except Exception as e:
                print("Command failure: %s\nException:%s" % (str(comm), str(e)))

    bot.log = []

    setupRawCommands(bot)

    bot.run(token)

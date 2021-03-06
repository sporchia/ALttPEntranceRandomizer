from BaseClasses import World
from Regions import create_regions
from EntranceShuffle import link_entrances, connect_entrance, connect_two_way, connect_exit
from Rom import patch_rom, LocalRom, write_string_to_rom, write_credits_string_to_rom
from Rules import set_rules
from Items import ItemFactory
from Main import create_playthrough
import random
import time
import logging
import argparse
import os
import hashlib

__version__ = '0.2-dev'

logic_hash = [182, 244, 144, 92, 149, 200, 93, 183, 124, 169, 226, 46, 111, 163, 5, 193, 13, 112, 125, 101, 128, 84, 31, 67, 107, 94, 184, 100, 189, 18, 8, 171,
              142, 57, 173, 38, 37, 211, 253, 131, 98, 239, 167, 116, 32, 186, 70, 148, 66, 151, 143, 86, 59, 83, 16, 51, 240, 152, 60, 242, 190, 117, 76, 122,
              15, 221, 62, 39, 174, 177, 223, 34, 150, 50, 178, 238, 95, 219, 10, 162, 222, 0, 165, 202, 74, 36, 206, 209, 251, 105, 175, 135, 121, 88, 214, 247,
              154, 161, 71, 19, 85, 157, 40, 96, 225, 27, 230, 49, 231, 207, 64, 35, 249, 134, 132, 108, 63, 24, 4, 127, 255, 14, 145, 23, 81, 216, 113, 90, 194,
              110, 65, 229, 43, 1, 11, 168, 147, 103, 156, 77, 80, 220, 28, 227, 213, 198, 172, 79, 75, 140, 44, 146, 188, 17, 6, 102, 56, 235, 166, 89, 218, 246,
              99, 78, 187, 126, 119, 196, 69, 137, 181, 55, 20, 215, 199, 130, 9, 45, 58, 185, 91, 33, 197, 72, 115, 195, 114, 29, 30, 233, 141, 129, 155, 159, 47,
              224, 236, 21, 234, 191, 136, 104, 87, 106, 26, 73, 250, 248, 228, 48, 53, 243, 237, 241, 61, 180, 12, 208, 245, 232, 192, 2, 7, 170, 123, 176, 160, 201,
              153, 217, 252, 158, 25, 205, 22, 133, 254, 138, 203, 118, 210, 204, 82, 97, 52, 164, 68, 139, 120, 109, 54, 3, 41, 179, 212, 42]


def main(args, seed=None):
    start = time.clock()

    # initialize the world
    world = World('vanilla', 'noglitches', 'standard', 'normal', 'ganon', 'freshness', False, False)
    logger = logging.getLogger('')

    hasher = hashlib.md5()
    with open(args.plando, 'rb') as plandofile:
        buf = plandofile.read()
        hasher.update(buf)
    world.seed = int(hasher.hexdigest(), 16) % 1000000000

    random.seed(world.seed)

    world.spoiler += 'ALttP Plandomizer Version %s  -  Seed: %s\n\n' % (__version__, args.plando)

    logger.info(world.spoiler)

    create_regions(world)

    world.spoiler += link_entrances(world)

    logger.info('Calculating Access Rules.')

    world.spoiler += set_rules(world)

    logger.info('Fill the world.')

    text_patches = []

    world.spoiler += fill_world(world, args.plando, text_patches)

    world.spoiler += print_location_spoiler(world)

    if world.get_entrance('Dam').connected_region.name != 'Dam' or world.get_entrance('Swamp Palace').connected_region.name != 'Swamp Palace (Entrance)':
        world.swamp_patch_required = True

    logger.info('Calculating playthrough.')

    try:
        world.spoiler += create_playthrough(world)
    except RuntimeError:
        if args.ignore_unsolvable:
            pass
        else:
            raise

    logger.info('Patching ROM.')

    if args.sprite is not None:
        sprite = bytearray(open(args.sprite, 'rb').read())
    else:
        sprite = None

    rom = LocalRom(args.rom)
    patch_rom(world, rom, logic_hash, args.quickswap, args.heartbeep, sprite)

    for textname, texttype, text in text_patches:
        if texttype == 'text':
            write_string_to_rom(rom, textname, text)
        elif texttype == 'credit':
            write_credits_string_to_rom(rom, textname, text)

    outfilebase = 'Plando_%s_%s' % (os.path.splitext(os.path.basename(args.plando))[0], world.seed)

    rom.write_to_file('%s.sfc' % outfilebase)
    if args.create_spoiler:
        with open('%s_Spoiler.txt' % outfilebase, 'w') as outfile:
            outfile.write(world.spoiler)

    logger.info('Done. Enjoy.')
    logger.debug('Total Time: %s' % (time.clock() - start))

    return world


def fill_world(world, plando, text_patches):
    ret = []
    mm_medallion = 'Ether'
    tr_medallion = 'Quake'
    logger = logging.getLogger('')
    with open(plando, 'r') as plandofile:
        for line in plandofile.readlines():
            if line.startswith('#'):
                continue
            if ':' in line:
                line = line.lstrip()

                if line.startswith('!'):
                    if line.startswith('!mm_medallion'):
                        _, medallionstr = line.split(':', 1)
                        mm_medallion = medallionstr.strip()
                    elif line.startswith('!tr_medallion'):
                        _, medallionstr = line.split(':', 1)
                        tr_medallion = medallionstr.strip()
                    elif line.startswith('!mode'):
                        _, modestr = line.split(':', 1)
                        world.mode = modestr.strip()
                    elif line.startswith('!logic'):
                        _, logicstr = line.split(':', 1)
                        world.logic = logicstr.strip()
                    elif line.startswith('!goal'):
                        _, goalstr = line.split(':', 1)
                        world.goal = goalstr.strip()
                    elif line.startswith('!light_cone_sewers'):
                        _, sewerstr = line.split(':', 1)
                        world.sewer_light_cone = sewerstr.strip().lower() == 'true'
                    elif line.startswith('!light_cone_lw'):
                        _, lwconestr = line.split(':', 1)
                        world.light_world_light_cone = lwconestr.strip().lower() == 'true'
                    elif line.startswith('!light_cone_dw'):
                        _, dwconestr = line.split(':', 1)
                        world.dark_world_light_cone = dwconestr.strip().lower() == 'true'
                    elif line.startswith('!fix_trock_doors'):
                        _, trdstr = line.split(':', 1)
                        world.fix_trock_doors = trdstr.strip().lower() == 'true'
                    elif line.startswith('!fix_trock_exit'):
                        _, trfstr = line.split(':', 1)
                        world.fix_trock_exit = trfstr.strip().lower() == 'true'
                    elif line.startswith('!fix_gtower_exit'):
                        _, gtfstr = line.split(':', 1)
                        world.fix_gtower_exit = gtfstr.strip().lower() == 'true'
                    elif line.startswith('!fix_pod_exit'):
                        _, podestr = line.split(':', 1)
                        world.fix_palaceofdarkness_exit = podestr.strip().lower() == 'true'
                    elif line.startswith('!fix_skullwoods_exit'):
                        _, swestr = line.split(':', 1)
                        world.fix_skullwoods_exit = swestr.strip().lower() == 'true'
                    elif line.startswith('!check_beatable_only'):
                        _, chkbtstr = line.split(':', 1)
                        world.check_beatable_only = chkbtstr.strip().lower() == 'true'
                    elif line.startswith('!save_quit_boss'):
                        _, sqbstr = line.split(':', 1)
                        world.save_and_quite_from_boss = sqbstr.strip().lower() == 'true'
                    elif line.startswith('!text_'):
                        textname, text = line.split(':', 1)
                        text_patches.append([textname.lstrip('!text_').strip(), 'text', text.strip()])
                    elif line.startswith('!credits_'):
                        textname, text = line.split(':', 1)
                        text_patches.append([textname.lstrip('!credits_').strip(), 'credits', text.strip()])
                    continue

                locationstr, itemstr = line.split(':', 1)
                location = world.get_location(locationstr.strip())
                if location is None:
                    logger.warn('Unknown location: %s' % locationstr)
                    continue
                else:
                    item = ItemFactory(itemstr.strip())
                    if item is not None:
                        world.push_item(location, item)
                    if item.key:
                        location.event = True
            elif '<=>' in line:
                entrance, exit = line.split('<=>', 1)
                ret.append(connect_two_way(world, entrance.strip(), exit.strip()))
            elif '=>' in line:
                entrance, exit = line.split('=>', 1)
                ret.append(connect_entrance(world, entrance.strip(), exit.strip()))
            elif '<=' in line:
                entrance, exit = line.split('<=', 1)
                ret.append(connect_exit(world, exit.strip(), entrance.strip()))

    world.required_medallions = (mm_medallion, tr_medallion)

    # set up Agahnim Events
    world.get_location('Agahnim 1').event = True
    world.get_location('Agahnim 1').item = ItemFactory('Beat Agahnim 1')
    world.get_location('Agahnim 2').event = True
    world.get_location('Agahnim 2').item = ItemFactory('Beat Agahnim 2')

    ret.append('\nMisery Mire Medallion: %s' % mm_medallion)
    ret.append('Turtle Rock Medallion: %s' % tr_medallion)
    ret.append('\n')
    return '\n'.join(ret)


def print_location_spoiler(world):
    return 'Locations:\n\n' + '\n'.join(['%s: %s' % (location, location.item if location.item is not None else 'Nothing') for location in world.get_locations()]) + '\n\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--create_spoiler', help='Output a Spoiler File', action='store_true')
    parser.add_argument('--ignore_unsolvable', help='Do not abort if seed is deemed unsolvable.', action='store_true')
    parser.add_argument('--rom', default='Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', help='Path to an ALttP JAP(1.0) rom to use as a base.')
    parser.add_argument('--loglevel', default='info', const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
    parser.add_argument('--seed', help='Define seed number to generate.', type=int)
    parser.add_argument('--quickswap', help='Enable quick item swapping with L and R.', action='store_true')
    parser.add_argument('--heartbeep', default='normal', const='normal', nargs='?', choices=['normal', 'half', 'quarter', 'off'],
                        help='Select the rate at which the heart beep sound is played at low health.')
    parser.add_argument('--sprite', help='Path to a sprite sheet to use for Link. Needs to be in binary format and have a length of 0x7000 (28672) bytes.')
    parser.add_argument('--plando', help='Filled out template to use for setting up the rom.')
    args = parser.parse_args()

    # ToDo: Validate files further than mere existance
    if not os.path.isfile(args.rom):
        input('Could not find valid base rom for patching at expected path %s. Please run with -h to see help for further information. \nPress Enter to exit.' % args.rom)
        exit(1)
    if not os.path.isfile(args.plando):
        input('Could not find Plandomizer distribution at expected path %s. Please run with -h to see help for further information. \nPress Enter to exit.' % args.plando)
        exit(1)
    if args.sprite is not None and not os.path.isfile(args.rom):
        input('Could not find link sprite sheet at given location. \nPress Enter to exit.' % args.sprite)
        exit(1)

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]
    logging.basicConfig(format='%(message)s', level=loglevel)

    main(args=args)

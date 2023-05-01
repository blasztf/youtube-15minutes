if __name__ == '__main':
    # step 0
    helper.log("PERFORMING: Preparing environment...")
    perform(prepare_environment(args.ffmpeg_path, args.use_data_api))
    
    if is_program_locked():
        exit("Program already opening!")

    lock_program()

    if args.prepare_only:
        lock_program(False)
        exit()
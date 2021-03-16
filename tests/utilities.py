""" Utility classes used to extend the unittest capabilities """


def write_dmr(output_dir: str, content: str):
    """ A helper function to write out the content of a `.dmr`, when the
        `harmony.util.download` function is called. This will be called as
        a side-effect to the mock for that function.

    """
    dmr_name = f'{output_dir}/downloaded.dmr'

    with open(dmr_name, 'w') as file_handler:
        file_handler.write(content)

    return dmr_name

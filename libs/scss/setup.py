from distutils.core import setup, Extension

setup(name='pyScss',
    version='1.1.1',
    description='pyScss',
    ext_modules=[
        Extension(
            '_scss',
            sources=['src/_scss.c', 'src/block_locator.c', 'src/scanner.c'],
            libraries=['pcre'],
            optional=True
        )
    ]
)

import numpy as np


def compare_nested_dict(d1, d2, path=''):
    for key in d1.keys():
        if key not in d2:
            print(d1.keys())
            print(d2.keys())
            raise KeyError('key is missing in d2: {}{}'.format(path, key))

        if isinstance(d1[key], dict):
            path += key + '.'
            compare_nested_dict(d1[key], d2[key], path)
        else:
            v1 = d1[key]
            v2 = d2[key]

            try:
                if isinstance(v1, np.ndarray):
                    assert (v1 == v2).all()
                elif isinstance(v1, tuple) or isinstance(v2, tuple):
                    # msgpack doesn't know about complex types, everything is
                    # an array. So tuples are packed as array and then
                    # unpacked as list by default.
                    assert list(v1) == list(v2)
                else:
                    assert v1 == v2
            except AssertionError:
                raise AssertionError('diff: {}{}'.format(path, key), v1, v2)
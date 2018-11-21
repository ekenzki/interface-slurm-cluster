# import charms.reactive.flags as flags
import charms.reactive as reactive
import socket

from charmhelpers.contrib.templating.contexts import dict_keys_without_hyphens
from charmhelpers.core.hookenv import (
    DEBUG,
    log,
)


class SlurmProvides(reactive.Endpoint):
    def send_controller_config(self, config):
        # have to handle every relation as there may be many different compute
        # node relations
        for rel in self.relations:
            rel.to_publish.update(config)

    def network_details(self):
        log("network_details: to_publish: {}"
            .format(self.relations[0].to_publish), level=DEBUG)
        return {
            'hostname': socket.gethostname(),
            'ingress_address': self.relations[0].to_publish['ingress-address']
        }

    def get_node_data(self):
        """Return a list of dictionaries with info for each node"""
        return self._get_all_nodes(keys=set(['ingress-address', 'hostname',
                                             'partition', 'inventory', 'default']))

    def _get_all_nodes(self, keys):
        """Return a list of dictionaries of values presented by remote units.

        :param set keys: A set of keys to retrieve from all remote units.
        :return: List of dictionaries with all values from all remote units.
        :rtype: list

        Example::

            >>> print(_get_all_nodes(keys=['hostname']))
            [
                { 'hostname': 'host1' },
                { 'hostname': 'host2' }
            ]

        """
        res = []
        for u in self.all_joined_units.values():
            received = u.received
            received_keys = set(received.keys())
            log("Processing node unit {}, received_keys: {}"
                .format(u.unit_name, received_keys), level=DEBUG)
            keys_present = received_keys.issuperset(keys)
            # skip a unit if it has not provided the necessary keys yet
            if not keys_present:
                log("Ignoring unit {}, received_keys: {}"
                    .format(u.unit_name, received_keys), level=DEBUG)
                continue
            res.append(dict_keys_without_hyphens(
                {k: received[k] for k in received_keys
                 if k in keys}))
            log("Added node unit {}, received_keys: {}"
                .format(u.unit_name, received_keys), level=DEBUG)
        return res

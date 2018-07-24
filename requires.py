import charms.reactive.flags as flags
import charms.reactive as reactive

from charmhelpers.core.hookenv import (
    log,
)


class SlurmRequires(reactive.Endpoint):

    def __init__(self, *args):
        super().__init__(*args)
        self._active_data = {}

    def _controller_relation(self):
        # can only be related to a single controller
        assert len(self.relations) < 2
        return self.relations[0]

    @property
    def ingress_address(self):
        return self._controller_relation().to_publish['ingress-address']

    def send_node_info(self, hostname, partition, default):
        # can only handle a single controller relation both active and
        # standby receive the same node info for this relation
        rel = self._controller_relation()
        log('Sending node info')
        rel.to_publish.update({
            'hostname': hostname,
            'partition': partition,
            'default': default,
        })

    def _controller_config_ready(self, config):
        '''Returns True if we find this node in the controller config.
        '''
        if config:
            log('Determining readiness by nodes from config: {}'.format(
                config.get('nodes')))
            nodes = config.get('nodes')
            for node in nodes:
                if node['ingress_address'] == self.ingress_address:
                    log('The controller is ready')
                    return True
        else:
            log('Controller is not ready as config is empty: {}'.format(
                repr(config)))
            return False

    @reactive.when('endpoint.{endpoint_name}.changed')
    def controllers_changed(self):
        """Assess related controllers and only take relation data from the
        active one"""
        self._active_data = self._controller_config()

        if self._controller_config_ready(self._active_data):
            flags.set_flag(self.expand_name(
                'endpoint.{endpoint_name}.active.available'))
            log('Set {} flag'.format(self.expand_name(
                'endpoint.{endpoint_name}.active.available')))
            flags.set_flag(self.expand_name(
                'endpoint.{endpoint_name}.active.changed'))
            log('Set {} flag'.format(self.expand_name(
                'endpoint.{endpoint_name}.active.changed')))
        else:
            log('Controller config not ready, clearing active.available'
                ' and active.changed flags')
            self.controller_broken()
            # TODO: JSON is not serializable => need to either remove
            # this and execute more or solve the problem
            # if helpers.data_changed('active_data', self._active_data):
            #    flags.set_flag(self.expand_name(
            #        'endpoint.{endpoint_name}.active.changed'))

        # processed the relation changed event - can clear this flag now
        flags.clear_flag(self.expand_name('changed'))
        log('Cleared {} flag'.format(self.expand_name('changed')))

    @reactive.when('endpoint.{endpoint_name}.departed')
    def controller_broken(self):
        flags.clear_flag(self.expand_name(
            'endpoint.{endpoint_name}.active.available'))
        log('Cleared {} flag'.format(self.expand_name(
            'endpoint.{endpoint_name}.active.available')))

        flags.clear_flag(self.expand_name(
            'endpoint.{endpoint_name}.active.changed'))
        log('Cleared {} flag'.format(self.expand_name(
            'endpoint.{endpoint_name}.active.changed')))

        flags.clear_flag(self.expand_name('departed'))
        log('Cleared {} flag'.format(self.expand_name('departed')))

    @property
    def active_data(self):
        return self._active_data

    def _controller_config(self):
        rel = self._controller_relation()

        log('Joined controller units: {}'.format(rel.joined_units))
        partitions = None
        recv_active = None
        for u in rel.joined_units:
            recv = u.received
            log('Received from {}: {}'.format(u.unit_name, recv))
            # the expectation is that backup controller units will not
            # post any config and there will only be one config posted
            # by the active controller
            cpartitions = recv.get('partitions')
            log('partitions: {}'.format(repr(partitions)))
            log('cpartitions: {}'.format(repr(cpartitions)))
            if partitions and cpartitions:
                log('Two controllers presenting active data: split-brain')
                # catch a split-brain condition when two controllers
                # advertise possibly conflicting config data which means
                # that active controller change
                # TODO: error/status handling for this
                flags.set_flag(self.expand_name(
                    'endpoint.{endpoint_name}.split-brain'))
            elif not partitions:
                log('Controller partitions: {}'.format(cpartitions))
                partitions = cpartitions
                recv_active = recv
        log('Active controller partitions: {}'.format(partitions))
        return recv_active if partitions else {}
